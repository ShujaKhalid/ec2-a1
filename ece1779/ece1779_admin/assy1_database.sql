-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

-- -----------------------------------------------------
-- Schema assignment1
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `assignment1` DEFAULT CHARACTER SET latin1 ;
USE `assignment1` ;

-- -----------------------------------------------------
-- Table `assignment1`.`students`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `assignment1`.`users` ;

CREATE TABLE IF NOT EXISTS `assignment1`.`users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `login` TEXT NOT NULL,
  `password` TEXT NOT NULL,
  PRIMARY KEY (`id`))
ENGINE = MyISAM
AUTO_INCREMENT = 3
DEFAULT CHARACTER SET = latin1;


-- -----------------------------------------------------
-- Table `assignment1`.`images`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `assignment1`.`images` ;

CREATE TABLE IF NOT EXISTS `assignment1`.`images` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `userId` TEXT NOT NULL,
  `key1` TEXT NOT NULL,
  `key2` TEXT NOT NULL,
  `key3` TEXT NOT NULL,
  `key4` TEXT NOT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
