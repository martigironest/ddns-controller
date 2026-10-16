variable "aws_region" {
  description = "Region of AWS where resources will be created"
  type        = string
  default     = "eu-west-1"
}

variable "instance_type" {
  description = "Type of EC2 instance to be created"
  type        = string
  default     = "t3.micro" # Covered by the AWS Free Tier
}

variable "key_name" {
  description = "Name of the SSH key created in AWS"
  type        = string
  default     = "ddns-key"
}