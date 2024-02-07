from flask import Flask, url_for, render_template, redirect, session
from werkzeug.security import check_password_hash, generate_password_hash
from Db import db
from Db.models import users, initiatives
from flask_migrate import Migrate