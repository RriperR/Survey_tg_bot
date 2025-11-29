# Base Python image
FROM python:3.13-alpine

# Timezone
RUN ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    echo "Europe/Moscow" > /etc/timezone

# Workdir inside container
WORKDIR /code

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Runtime env
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/code"

# Start bot as a module so that package imports like `app.*` work
CMD ["python", "-m", "app.bot"]