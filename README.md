# Tytovision IoT Camera Software

For installation

- Download "tyto_camera_installer.sh" and "s3_get.sh" files from S3 bucket under "tytovision/iot_control/install"
- Move the files "/home/pi" directory without any parent folder
- Set enviroment variables as:
  - export AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>
  - export AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>
  - export GITHUB_TOKEN=<GITHUB_TOKEN>
- Execute "sudo -E sh ./tyto_camera_installer.sh"
