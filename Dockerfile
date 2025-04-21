# Use the official AWS Lambda Python base image matching the SAM template Runtime and Architecture
FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.13

# Set the working directory in the container
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# Using --no-cache-dir can reduce image size
# Use --upgrade pip first for potentially newer versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the src directory itself into the working directory
COPY src/ ${LAMBDA_TASK_ROOT}/src/
