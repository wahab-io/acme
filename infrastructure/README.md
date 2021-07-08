# Infrastructure

This cdk project is primarily responsible for deploying infrastructure resources that are necessary to run the successful SDLC. Below is the list of components that will be configured as part of this stack:

- ECS Cluster to run each component in containers
- Jenkins
- SonarQube (Coming)




# Limitations

- Due to lack of support for AWS Cloud Map to provision Private DNS Hosted Zone in shared VPC via AWS RAM, we have to rely on container IP addresses for communication. Once, the Jenkins is up and running, under `Manage Jenkins` go to, `Manage Nodes and Cloud` and then click `Configure Clouds`. Under Amazon EC2 Container Service Cloud, expand by clicking `Advanced...` and then update the `Alternate Jenkins URL` value to appropiate assigned Jenkins controller **IP Address** and **Port**. e.g. `http://10.0.x.x:8080` (if your network is based on CIDR range of `10.0.0.0/16`)