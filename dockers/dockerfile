# docker build -t wfpb-glycosight-interface -f dockerfile .
FROM wfpb:glycosight-interface-base

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--access-logfile", "/var/log/gunicorn/dev.log", "wsgi:app"]
