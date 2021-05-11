import yaml
import requests
import os
from aws_credentials import *
from logger import *
import tarfile

logger=TytoLog()
script_path=os.path.dirname(os.path.realpath(__file__))

def get_members(tar_file, prefix):
    def set_path(tarinfo):
        tarinfo.path=tarinfo.path.split('/', 1)[-1]
        return tarinfo
    return [set_path(tarinfo) for tarinfo in tar_file.getmembers() if "{:s}/".format(prefix) in tarinfo.name]


current_version=None

with open(os.path.join(script_path,'version.yaml')) as file:
    # The FullLoader parameter handles the conversion from YAML
    # scalar values to Python the dictionary format
    version_props = yaml.load(file, Loader=yaml.FullLoader)
    current_version=version_props["version"]
    logger.logger.info("Current Version is : {:s}".format(str(current_version)))

if current_version is not None:
    response = requests.get("https://api.github.com/repos/Tytovision/iot_control/releases/latest?access_token={:s}".format(GITHUB_TOKEN))
    if response.json()["tag_name"]!=current_version:
        new_release=response.json()["tarball_url"]
        target_path = os.path.join(script_path,'latest.tar.gz')
        response = requests.get("{:s}?access_token={:s}".format(new_release, GITHUB_TOKEN), stream=True)
        if response.status_code == 200:
            with open(target_path, 'wb') as f:
                f.write(response.raw.read())
            if os.path.exists(target_path):
                tar = tarfile.open(target_path, "r:gz")
                tar.extractall(path=os.path.abspath(os.path.join(script_path, os.pardir)), members=get_members(tar, "tytocam"))
                tar.close()




