from django.conf import settings
import django
import sys


settings.configure(
    SECRET_KEY = '2^^i8=bdv=jnm30qbz5@$!(q-(%ap-95+30)-e_hksrk_l#a72',
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'tytoserver',
            'USER': 'tytoadmin',
            'PASSWORD': '247520',
            'HOST': '18.158.219.166',
            'PORT': '5432',
        }
    },
    INSTALLED_APPS=[
        'django_orm.Video_Files',
        'django_orm.AdminPanel',
        'django_orm.Maps',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django_orm.Users',
        'django.contrib.postgres',

    ],
    AUTH_USER_MODEL = 'Users.TytoUser',

)
django.setup()



