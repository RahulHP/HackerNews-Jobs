Deployment Steps
```
aws cloudformation deploy --template-file cloudformation/job_database.yaml --stack-name jobdatabase --parameter-overrides rdsuser=admin rdspassword=password rdsport=3306
aws cloudformation deploy --template-file cloudformation/user_database.yaml --stack-name userdatabasedev --parameter-overrides env=dev


aws cloudformation package --template cloudformation/cognito.yaml --s3-bucket hn-jobs-rahulhp-dev --output-template-file cloudformation/cognito_gen.yaml
aws cloudformation deploy --template-file cloudformation/cognito_gen.yaml --stack-name cognitotest --parameter-overrides env=test --capabilities CAPABILITY_NAMED_IAM

aws cloudformation deploy --template-file cloudformation/ec2server.yaml --stack-name serverdev --capabilities CAPABILITY_NAMED_IAM --parameter-overrides env=dev keyname=key securitygroup=group FlaskSessionKey=secret

aws s3api create-bucket --acl private --bucket hn-jobs-rahulhp-dev --region us-east-1

aws cloudformation package --template cloudformation\lambdas.yaml --s3-bucket hn-jobs-rahulhp-dev --output-template-file cloudformation\lambda_gen.yaml

aws cloudformation deploy --template-file cloudformation\lambda_gen.yaml --stack-name lambdastackdev --capabilities CAPABILITY_NAMED_IAM --parameter-overrides env=dev
```

After SSHing into EC2

1. Add `export ENV=dev` line to `~/.bashrc`
2. `source ~/.bashrc`
3. `mkdir hnjobs`
4. `cd hnjobs`
5. `git clone https://github.com/RahulHP/HackerNews-Jobs.git`
6. `cd HackerNews-Jobs`
7. `bash setup.sh`
8. Update environment values in `https.sh`, `nginx_setup/app`, `nginx_setup/app.service`, `nginx_setup/backend.service`
9. `bash https.sh`
10. `bash deployment.sh`