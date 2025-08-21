from setuptools import setup, find_packages

setup(
    name="app_manage_token",
    version="1.0.0",
    description="Aplicación Flask con autenticación y manejo de sesiones activas",
    author="dev-ojeda",
    author_email="neo1sr3@email.com",
    url="https://github.com/dev-ojeda/poc-manage-token",
    platforms=["any"],
    packages=find_packages(),
    package_dir={"app": "app"},  # raíz de los paquetes
    install_requires=[
        "Flask",
        "pymongo",
        "python-dotenv",
        "pyjwt",
        "flask-cors",
        "dnspython",
        "gunicorn",  # opcional si usarás despliegue en producción
    ],
    entry_points={
        "console_scripts": [
            "app_manage_token=app:main",  # si tienes una función main() en myapp/app.py
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Flask",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)

