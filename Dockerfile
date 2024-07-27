FROM python:3.12.4-alpine

# permissions and nonroot user for tightened security
RUN adduser -D nonroot
RUN mkdir /home/app/ && chown -R nonroot:nonroot /home/app
WORKDIR /home/app
USER nonroot

# copy all the files to the container
COPY --chown=nonroot:nonroot . .

RUN pip3 install -r requirements.txt

CMD ["python3", "main.py"]
