import boto3

db_config = {'user': 'instanceuser', 
             'password':'',
             'host': '52.87.157.40',
             'database': 'assignment1'}
			 
ami_id = 'ami-b547f2a3'
database_id = 'i-083b597b9fab4f5c6' 

# Launch the initial instance and capture its IP-address and instance ID 
ec2 = boto3.resource('ec2')
client = boto3.client('elb')
instances = ec2.instances.all()

# instance = ec2.create_instances(ImageId=ami_id, MinCount=1, Monitoring={'Enabled':True},SecurityGroups=["launch-wizard-5"], MaxCount=1, InstanceType='t2.small')

# Wait for the instance to enter the running state:
# instance.wait_until_running()

# Reload the instance attributes:
# instance.load()

# Register instance with load balancer:
for i in instances:
    if i.id != database_id:
        if i.state[('Name')] == 'running': 
            response = client.register_instances_with_load_balancer(
            LoadBalancerName='ec2-load-balancer-a1',
            Instances=[{'InstanceId': i.id},]
        )

#     inst_ip = i.public_dns_name
#     inst_id = i.id

#     print('Newly created instance: ' + str(inst_id) + ' added to load balancer')
#     print('Instance running on port 5000 (IP Address = ' + str(inst_ip) + ')')

     
