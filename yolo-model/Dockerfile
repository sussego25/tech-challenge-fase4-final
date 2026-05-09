FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310-ubuntu20.04-sagemaker

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      ultralytics \
      pillow \
      numpy \
      opencv-python-headless
