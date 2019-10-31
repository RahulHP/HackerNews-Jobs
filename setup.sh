wget https://repo.anaconda.com/miniconda/Miniconda3-4.6.14-Linux-x86_64.sh
bash Miniconda3-4.6.14-Linux-x86_64.sh -b
source ~/miniconda3/bin/activate
conda init
source ~/.bashrc

conda create -y --name webapp flask boto3 requests pymysql
conda activate webapp
conda install -y -c conda-forge uwsgi
sudo apt install -y nginx
# https://github.com/ContinuumIO/anaconda-issues/issues/11159