FROM python:slim

WORKDIR /workspace

COPY . ./

# RUN printf 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ buster main contrib non-free\n'\
# '# deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ buster main contrib non-free\n'\
# 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ buster-updates main contrib non-free\n'\
# '# deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ buster-updates main contrib non-free\n'\
# 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ buster-backports main contrib non-free\n'\
# '# deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ buster-backports main contrib non-free\n'\
# 'deb https://mirrors.tuna.tsinghua.edu.cn/debian-security buster/updates main contrib non-free\n'\
# '# deb-src https://mirrors.tuna.tsinghua.edu.cn/debian-security buster/updates main contrib non-free' > /etc/apt/sources.list

RUN apt-get update && apt-get install -y gcc build-essential libssl-dev libffi-dev python-dev


# RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt 
RUN pip install -r requirements.txt && python main.py --initdb

CMD ["sh","-c", "python main.py"]