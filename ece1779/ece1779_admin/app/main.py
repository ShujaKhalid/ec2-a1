from flask import render_template, redirect, url_for, request, g, session
from math import floor
from app import webapp
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app import config
from app.config import db_config
from datetime import datetime, timedelta
from operator import itemgetter
import decimal
import time
import atexit
import random
import boto3
import sys
import mysql.connector
import numpy
import logging

webapp.secret_key = '\x80\xa9s*\x12\xc7x\xa9d\x1f(\x03\xbeHJ:\x9f\xf0!\xb1a\xaa\x0f\xee'
logging.basicConfig()
scheduler = BackgroundScheduler(standalone=True)

@webapp.route('/', methods=['GET'])
@webapp.route('/index', methods=['GET'])
@webapp.route('/main', methods=['GET'])
# Display an HTML page with links
def main():
    # return render_template("uploadForm.html", title="UserUI") # For LoadGenerator
    return render_template("main.html", title="UserUI")

def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   database=db_config['database'])

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@webapp.route('/login', methods=['GET', 'POST'])
def login():
    return render_template("login.html")

@webapp.route('/login_submit', methods=['GET', 'POST'])
def login_submit():

    cnx = get_db()
    cursor = cnx.cursor()
    query = "SELECT DISTINCT login, password FROM users WHERE login = %s"
    user = request.form['username']
    cursor.execute(query, (user,))
    row = cursor.fetchone()

    error_msg = "Error: User with provided credentials does not exist!"

    if 'username' in request.form and row != None \
        and request.form['username'] == row[0] and \
        'password' in request.form and \
        request.form['password'] == row[1]:

        session['authenticated'] = True
        session['username'] = request.form['username']
        session['password'] = request.form['password']

        # Let's use Amazon S3
        s3 = boto3.resource('s3')
        # Print out bucket names
        buckets = s3.buckets.all()
        for b in buckets:
            name = b.name

        if request.form['username'] == 'admin':
            return redirect(url_for('admin_view'))
        return redirect(url_for('s3_view', id=name))

    return render_template("login.html", error_msg=error_msg)

@webapp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@webapp.route('/create_account', methods=['GET', 'POST'])
def create_account():
    return redirect(url_for('user_create'))


@webapp.route('/admin', methods=['GET'])
def admin_view():
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    cpuutil = {}
    tempvar = ''

    for i in instances:
        tempvar = ec2_cpuutil_calc(i.id)
        cpuutil[i.id] = (tempvar)

    return render_template("admin/list.html", title="Workers and CPU Utilization", instances=instances, cpuutil=cpuutil)


@webapp.route('/ec2_cpuutil_calc/<id>',methods=['GET'])
#Display details about a specific instance.
def ec2_cpuutil_calc(id):
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(id)
    client = boto3.client('cloudwatch')
    metric_name = 'CPUUtilization'

    namespace = 'AWS/EC2' 
    statistic = 'Average'                   # could be Sum,Maximum,Minimum,SampleCount,Average

    cpu = client.get_metric_statistics(
        Period=1 * 60,
        # StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
	StartTime=datetime.utcnow() - timedelta(seconds=3 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
	MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    cpu_stats = []
    cpu_util = []
    max_cpu_vals = 0

    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        cpu_util.append(int(point['Average']))
           # print(point['Average'], file = sys.stderr)

    if (cpu_util != []):
        max_cpu_vals = max(cpu_util)

    if (max_cpu_vals == 0):
        return 0
    else: 
        return max_cpu_vals

@webapp.route('/admin/create', methods=['POST'])
# Start a new EC2 instance
def ec2_create():

    ec2 = boto3.resource('ec2')

    ec2.create_instances(ImageId=config.ami_id, MinCount=1, Monitoring={'Enabled':True},SecurityGroups=["launch-wizard-5"],
                         MaxCount=1, InstanceType='t2.small')

    return redirect(url_for('admin_view'))


@webapp.route('/admin/delete/<id>', methods=['GET', 'POST'])
# Terminate a EC2 instance
def ec2_destroy(id):
    # create connection to ec2
    ec2 = boto3.resource('ec2')

    ec2.instances.filter(InstanceIds=[id]).terminate()

    return redirect(url_for('admin_view'))


@webapp.route('/admin/autoscale/', methods=['GET', 'POST'])
# Launch auto-scaling Template
def ec2_autoscale():
    return render_template("admin/autoscale.html")

@webapp.route('/admin/monitor_instance/', methods=['GET', 'POST'])
def monitor_instance(uplimit, lowlimit, expratio, shrinkratio):

    ec2 = boto3.resource('ec2')
    client = boto3.client('cloudwatch')
    client_lb = boto3.client('elb')
    qInst = 1
    count = 0
    count_run = 0
    count_term = 0
    count_pen = 0
    MaxCount = qInst * expratio
    MinCount = qInst
    cpu_alarm = False

    metric_name = 'CPUUtilization'
    namespace = 'AWS/EC2'
    statistic = 'Average'
    max_cpu_vals = []
    cpu_util = []
    cpu_util_sum = 0
    instances = ec2.instances.all()
    add_workers = 0
    current_workers = 0

    for d in instances:
        if (d.id != config.database_id): # Do not include the MySql server in calculations
            if (d.state[('Name')] == 'running'):
                count_run = count_run + 1
                cpu_util_sum = cpu_util_sum + ec2_cpuutil_calc(d.id)
            elif (d.state[('Name')] == 'pending'):
                count_pen = count_pen + 1
            elif (d.state[('Name')] == 'terminated'):
                count_term = count_term + 1

    count = count_run + count_term + count_pen # total number of available workers

    if count_run > 0:
    	max_cpu_vals.append(int(cpu_util_sum)/int(count_run+count_pen))

    print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    print('Scheduled Operations running in Background (CloudWatch)')
    # print('UserI Server IP Address (Public) = ' + config.inst_ip)
    print('MySql Server IP Address (Public) = 52.87.157.40')
    print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    print('No of instances in worker pool: ' + str(count_run + count_pen))
    print('Avg. load experinced between instance: ' + str(max_cpu_vals))    

    print('----------------------------------------------------------')
    print('Load Balancer Health Checker')
    # print('----------------------------------------------------------')

    response = client_lb.describe_instance_health(LoadBalancerName='ec2-load-balancer-a1',)
    for i in response['InstanceStates']: 
       for u in i:
           if u == 'InstanceId':
               inst_temp = i[u]
	   if u == 'State':
	       # if i[u] == 'InService':
    	       print('InstanceId = ' + inst_temp + ' --> Health = ' + i[u])

    # Assign healthy workers to the value for available workers
    current_workers = count_run + count_pen

    # Determine the no. of instances required if the required thresholds
    # aren't met
    if (max_cpu_vals != []):
        if (max(max_cpu_vals) > int(uplimit)):
            add_workers = (int(current_workers) * int(expratio)) - int(current_workers)
	    # Only grow pool if the total number of workers is less than the max
            # limit (50)
            if ((current_workers + add_workers) < 50):
                # Grow worker pool
                print('------------------------')
		print('Growing worker pool!')
		grow_worker_pool(add_workers)
            else:
                print('------------------------')
                print('Pool resizing not required!')
		print('Desired Pool Size = ' + str(current_workers + add_workers) + ' is greater than the max limit (20)')
        elif (max(max_cpu_vals) < int(lowlimit)):
            rem_workers = int(current_workers) - floor(int(current_workers) / int(shrinkratio))
            # print('Desired Pool Size = ' + str(current_workers - rem_workers))
            # print('Current Workers   = ' + str(current_workers))
            # Only shrink pool if the total number of workers is greater than the
            # min required (1)
            if (rem_workers > 0):
                if ((int(current_workers) - int(rem_workers)) > 0):
                    # Shrink worker pool
		    print('------------------------')
		    print('Shrinking Worker Pool!')
                    shrink_worker_pool(rem_workers, instances)
            else:
                print('------------------------')
		print('Pool resizing not required!')
                print('Desired Pool Size = ' + str(current_workers - rem_workers) + ' is less than the min required workers (1)')
        else:
            print('----------------------------------------------------------')
            print('Current Pool Size = ' + str(current_workers))
	    print('Application operating wiithin acceptable thresholds. No changes required!')	    


    print('----------------------------------------------------------')
    print('Waiting for next scheduled trigger...')
    print('----------------------------------------------------------')
    
    return

@webapp.route('/admin/grow_worker_pool/', methods=['POST'])
# Grow the worker pool based on pre-defined expansion ratio:
def grow_worker_pool(add_workers):
    ec2 = boto3.resource('ec2')
    client = boto3.client('elb')
    if (add_workers != 0):
        response = ec2.create_instances(ImageId=config.ami_id, MinCount=add_workers, Monitoring={'Enabled':True},SecurityGroups=["launch-wizard-5"], MaxCount=add_workers, InstanceType='t2.small')
        # Register instance with load balancer:
        for i in response:
	    print(str(i.id) + 'has been launched and registered to the load balancer')
            ec2_register_instance(i.id)

    return


@webapp.route('/admin/shrink_worker_pool/', methods=['POST'])
# Shrink the worker pool based on pre-defined shrinkage ratio:
def shrink_worker_pool(rem_workers, instances):
    ec2 = boto3.resource('ec2')
    client = boto3.client('cloudwatch')
    clt = boto3.client('ec2')
    # Create a list of terminateable instances:
    instances_to_terminate = []
    for i in instances:
        if (i.state[('Name')] == 'running'):
            if ((i.id != config.database_id) ):  # Do not delete the main instance or the MySql server!
                response = clt.describe_instance_attribute(InstanceId=i.id, Attribute='disableApiTermination')
                if response[('DisableApiTermination')][('Value')] == False:
                    instances_to_terminate.append(i.id)
                    # ec2_deregister_instance(i.id)
		    # print('Instance to Terminate: ' + str(i.id))

    for i in instances_to_terminate[0:int(rem_workers)]:
        print(str(i) + ' has been terminated and deregistered from the load balancer')
        ec2.instances.filter(InstanceIds=[i]).terminate()
	ec2_deregister_instance(i)

    return

@webapp.route('/admin/autoscale_config/', methods=['POST'])
# Set configuration parameters for Auto-Scaling:
def ec2_autoscale_config():

    uplimit = (request.form.get('uplimit'))
    lowlimit = (request.form.get('lowlimit'))
    expratio = (request.form.get('expratio'))
    shrinkratio = (request.form.get('shrinkratio'))

    # ec2_load_balancer()

    # scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(
        func=monitor_instance,
        args=[uplimit, lowlimit, expratio, shrinkratio],
        trigger=IntervalTrigger(seconds=5),
        id='monitoring_job',
        name='Monitor CPUUtilization of instances',
        replace_existing=True
    )
	
    print('Background Scheduler Running')    

    return redirect(url_for('admin_view'))

@webapp.route('/admin/autoscale_stop/', methods=['POST'])
# Stop background Scheduler
def ec2_autoscale_stop():
    
    scheduler.pause()
    
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()

    for i in instances:
	if i.id != config.database_id:
            ec2.instances.filter(InstanceIds=[i.id]).terminate()
            ec2_deregister_instance(i.id)

    print('Scheduler Stopped and Instances deleted!')

    return 'Scheduler Stopped!'

@webapp.route('/admin/ec2_load_balancer/', methods=['POST'])
# Set configuration parameters for Auto-Scaling:
def ec2_load_balancer():

    ec2 = boto3.resource('ec2')
    client = boto3.client('elb')

    response = client.create_load_balancer(
    AvailabilityZones=[
        'us-east-1b',
    ],
    Listeners=[
        {
            'InstancePort': 80,
            'InstanceProtocol': 'HTTP',
            'LoadBalancerPort': 80,
            'Protocol': 'HTTP',
        },
    ],
    LoadBalancerName='ec2-load-balancer-a1',
    )

    return 

@webapp.route('/admin/ec2_register_instance/', methods=['POST'])
# Set configuration parameters for Auto-Scaling:
def ec2_register_instance(id):

    ec2 = boto3.resource('ec2')
    client = boto3.client('elb')

    response = client.register_instances_with_load_balancer(
    LoadBalancerName='ec2-load-balancer-a1',
    Instances=[{'InstanceId': id},]
    )
    print('Instance: ' + id + ' added to load balancer')
    return

@webapp.route('/admin/ec2_deregister_instance/', methods=['POST'])
# Set configuration parameters for Auto-Scaling:
def ec2_deregister_instance(id):

    client = boto3.client('elb')

    response = client.deregister_instances_from_load_balancer(
    LoadBalancerName='ec2-load-balancer-a1',
    Instances=[{'InstanceId': id},]
    )

    print('Instance: ' + id + ' removed from load balancer')
    return

# @webapp.route('/login_submit_test', methods=['GET', 'POST'])
# def login_submit_test():

#     cnx = get_db()
#     cursor = cnx.cursor()
#     query = "SELECT DISTINCT login, password FROM users WHERE login = %s"
#     user = request.form['userID']
#     cursor.execute(query, (user,))
#     row = cursor.fetchone()

#     uploadedfile = request.form['uploadedfile'] 

#     if 'userID' in request.form and row != None \
#         and request.form['userID'] == row[0] and \
#         'password' in request.form and \
#             request.form['password'] == row[1]:

#         # print('%%%Debug%%%', file=sys.stderr)
#         session['authenticated'] = True
#         session['username'] = request.form['userID']
#         session['password'] = request.form['password']
#         session['uploadedfile'] = request.form['uploadedfile'] 
#         # Let's use Amazon S3`
#         s3 = boto3.resource('s3')
#         # Print out bucket names
#         buckets = s3.buckets.all()
#         for b in buckets:
#             name = b.name

#         session['name'] = name # For Testing

#         if request.form['userID'] == 'admin':
#             return redirect(url_for('admin_view'))
#         else:        
#             # return redirect(url_for('s3_upload_test', id=name, uploadedfile=uploadedfile))
#             return redirect(url_for('s3_upload_test'))

#     else: 
#         return redirect(url_for('login'))

@webapp.route('/admin/ec2_nuke/', methods=['POST'])
# Set configuration parameters for Auto-Scaling:
def ec2_nuke():
    # S3 delete everything in S3 bucket
    s3 = boto3.resource('s3')
    id = 'ece1779bucket1'
    s3.Bucket(id).objects.delete()

    # Delete everything in relational database
    # cnx = get_db()
    # cursor = cnx.cursor()
    # query = "DELETE FROM users"
    # cursor.execute(query)
    # cnx.commit()

    cnx = get_db()
    cursor = cnx.cursor()
    query = "DELETE FROM images"
    cursor.execute(query)
    cnx.commit()

    return admin_view()

