import subprocess


def get_installed_packages():
    # Execute pip freeze and get the output
    installed_packages = subprocess.check_output(["pip", "freeze"]).decode("utf-8").splitlines()

    # Parse the output to get the package names
    installed_packages = [package.split('==')[0] for package in installed_packages]

    return installed_packages


def get_lambda_packages():
    # List of libraries available in AWS Lambda by default
    lambda_packages = ['boto3', 'botocore', 'docutils', 'jmespath', 'pip', 'python-dateutil', 's3transfer',
                       'setuptools', 'six', 'urllib3']

    return lambda_packages


def get_non_lambda_packages():
    installed_packages = get_installed_packages()
    lambda_packages = get_lambda_packages()

    # Filter the installed packages to get the ones that are not available in AWS Lambda by default
    non_lambda_packages = [package for package in installed_packages if package not in lambda_packages]

    return non_lambda_packages


def generate_requirements_file():
    # Get the list of non-lambda packages
    non_lambda_packages = get_non_lambda_packages()

    # Write the list of non-lambda packages to a file
    with open('requirements.txt', 'w') as f:
        for package in non_lambda_packages:
            f.write(f"{package}\n")


generate_requirements_file()
