FROM python:3.12.4-alpine

RUN adduser -D nonroot
RUN mkdir /home/app/ && chown -R nonroot:nonroot /home/app
WORKDIR /home/app
USER nonroot

# to enable cache of requirements.txt
COPY --chown=nonroot:nonroot  ./requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt

COPY --chown=nonroot:nonroot ./main.py ./main.py

CMD ["python3", "main.py"]
