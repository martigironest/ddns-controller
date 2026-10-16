output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.ddns_server.public_ip
}

output "ssh_connection_command" {
  description = "SSH command to connect to the EC2 instance"
  value       = "ssh -i ~/.ssh/ddns-key.pem ubuntu@${aws_instance.ddns_server.public_ip}"
}