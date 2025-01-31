#!/bin/bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 130.193.45.98:5000 
