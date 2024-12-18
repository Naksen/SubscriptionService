import os
from pathlib import Path

from apps.back import celery_app
from apps.back.settings import task_groups

python_path = "python3"
log_path = "/var/log/celery/"


def clear_all_tasks() -> None:
    celery_app.control.purge()


def get_workers() -> list[str]:
    """Формирует список воркеров"""
    workers = []
    for item in celery_app.conf.task_routes.items():
        worker = item[1]["queue"]
        if worker not in workers:
            workers.append(worker)
    return workers


def get_beats() -> list[str]:
    """Формирует список битов"""
    return [beat for beat in task_groups]


def make_beat_comand(
    beat_name: str,
    is_start: bool,
    python_path: str = python_path,
    log_path: str = log_path,
) -> str:
    """Формирует команду для запуска или остановки бита"""
    cmd = ""
    if is_start:
        cmd = (
            f"TASK={beat_name} {python_path} -m celery -A apps.back beat -l WARNING --detach "
            f'--logfile="{log_path}{beat_name}.log" --pidfile="{log_path}{beat_name}.pid"'
        )
    else:
        cmd = f'kill "$(cat /var/log/celery/{beat_name}.pid)"'
    print(f"Beat cmd: {cmd}")
    return cmd


def start_or_stop_worker(worker_list: list[str], is_start: bool) -> None:
    """Запускает или останавливает воркеры из списка"""

    # Если нет файла с логами - создаем
    if not os.path.exists(f"{log_path}workers.log"):
        with open(f"{log_path}workers.log", "w"):
            pass

    cmd = (
        f"{python_path} -m celery -A apps.back multi {'start' if is_start else 'stop'} 2 "
        f'-l WARNING --autoscale=10,4 --pidfile="{log_path}%n.pid" --logfile="{log_path}workers.log" '
        f"-Q {','.join(worker_list)}"
    )

    print(f"Worker cmd: {cmd}")

    os.system(cmd)


def start_or_stop_beats(beat_list: list[str], is_start: bool) -> None:
    "Запускает или останавливает биты из списка"
    for beat in beat_list:
        if is_start:
            cmnd = make_beat_comand(beat, is_start=True)
            os.system(cmnd)
            print(f"Бит {beat} запущен")
        else:
            cmnd = make_beat_comand(beat, is_start=False)
            os.system(cmnd)
            print(f"Бит {beat} остановлен")


def beat_is_start(beat_name: str, log_path: str = log_path) -> bool:
    return Path(f"{log_path}{beat_name}.pid").exists()


def available_workers() -> dict[str, str] | None:
    started_workers = celery_app.control.inspect().active()
    if not started_workers:
        workers = get_workers()
        available_workers = {}
        count = 1
        for worker in workers:
            available_workers[str(count)] = worker
            count += 1
        return available_workers
    else:
        worker_list = get_workers()
        for worker in started_workers:
            worker_name = worker.split("-")[0]
            if worker_name in worker_list:
                worker_list.remove(worker_name)
            else:
                print(f"{worker_name} not in working list")
        if not worker_list:
            return None
        else:
            available_workers = {}
            count = 1
            for worker in worker_list:
                available_workers[str(count)] = worker
                count += 1
            return available_workers


def running_workers() -> dict[str, str] | None:
    started_workers = celery_app.control.inspect().active()
    if not started_workers:
        return None
    running_workers = {}
    count = 1
    for worker in started_workers:
        worker_name = worker.split("-")[0]
        running_workers[str(count)] = worker_name
        count += 1
    return running_workers


def available_beats() -> dict[str, str]:
    beat_list = get_beats()
    available_beats = {}
    count = 1
    for beat in beat_list:
        if not beat_is_start(beat):
            available_beats[str(count)] = beat
            count += 1
    return available_beats


def running_beats() -> dict[str, str]:
    beat_list = get_beats()
    run_beats = {}
    count = 1
    for beat in beat_list:
        if beat_is_start(beat):
            run_beats[str(count)] = beat
            count += 1
    return run_beats


def clearcelery(workers: list[str], python_path: str = python_path) -> None:
    for worker in workers:
        print(f"Очистка {worker}")
        cmd = f"{python_path} -m celery -A apps.back purge -f -Q {worker}"
        os.system(cmd)
    print("Команда успешно выполнена")


def remove_pid_files() -> None:
    for f in os.listdir(log_path):
        if f.endswith(".pid"):
            Path(os.path.join(log_path, f)).unlink()


def run(*args) -> None:  # type: ignore
    Path(log_path).mkdir(parents=True, exist_ok=True)

    flag: list[str] | bool = list(args) if args else True

    while flag:
        if args:
            assert isinstance(flag, list)
            answer = flag.pop(0)
        else:
            answer = input(
                "\n "
                "Выберите действие:\n "
                "1 - запустить все биты, \n "
                "2 - остановить все биты, \n "
                "3 - запустить бит, \n "
                "4 - остановить бит, \n "
                "5 - запустить все воркеры, \n "
                "6 - остановить все воркеры, \n "
                "7 - запустить воркер, \n "
                "8 - остановить воркер, \n "
                "9 - запустить Celery, \n "
                "10 - остановить Celery, \n "
                "11 - запустить Flower, \n "
                "12 - посмотреть запущенные воркеры, \n "
                "13 - очистить Celery, \n "
                "14 - Открыть логи Celery, \n"
                "15 - выйти \n"
                ":",
            )

        if answer == "1":
            beat_list = get_beats()
            remove_pid_files()
            start_or_stop_beats(beat_list, is_start=True)

        elif answer == "2":
            beat_list = get_beats()
            start_or_stop_beats(beat_list, is_start=False)

        elif answer == "3":
            print("Биты доступные для запуска:")
            beats = available_beats()
            if beats:
                for key, value in beats.items():
                    print(f"{key} - {value}")
                answer = (input("Введите номера битов через пробел: ")).split(" ")  # type: ignore
                beat_list = [beats[num] for num in answer]

                start_or_stop_beats(beat_list, is_start=True)
            else:
                print("Все биты запущены")
        elif answer == "4":
            print("Запущенные биты:")
            beats = running_beats()
            if beats:
                for key, value in beats.items():
                    print(f"{key} - {value}")
                beat_nums: list[str] = (
                    input("Введите номера битов через пробел: ")
                ).split(" ")
                beat_list: list[str] = [beats[num] for num in beat_nums]

                start_or_stop_beats(beat_list, is_start=False)
            else:
                print("Запущенные биты отсутствуют")
        elif answer == "5":
            workers = get_workers()
            start_or_stop_worker(workers, is_start=True)
        elif answer == "6":
            workers = get_workers()
            start_or_stop_worker(workers, is_start=False)
        elif answer == "7":
            workers = available_workers()
            if not workers:
                print("Все воркеры запущены")
            else:
                print("Доступные воркеры: ")
                for key, value in workers.items():
                    print(f"{key} - {value}")
                answer = (input("Введите номера воркеров через пробел: ")).split(" ")
                worker_list: list[str] = [workers[num] for num in answer]

                start_or_stop_worker(worker_list, is_start=True)
        elif answer == "8":
            workers = running_workers()
            if not workers:
                print("Запущенные воркеры отсутствуют")
            else:
                print("Запущенные воркеры: ")
                for key, value in workers.items():
                    print(f"{key} - {value}")
                answer = (input("Введите номера воркеров через пробел: ")).split(" ")
                worker_list = [workers[num] for num in answer]

                start_or_stop_worker(worker_list, is_start=False)
        elif answer == "9":
            beats = get_beats()
            workers = get_workers()
            remove_pid_files()
            start_or_stop_beats(beat_list=beats, is_start=True)
            start_or_stop_worker(worker_list=workers, is_start=True)
        elif answer == "10":
            beats = get_beats()
            workers = get_workers()
            remove_pid_files()
            start_or_stop_beats(beat_list=beats, is_start=False)
            start_or_stop_worker(worker_list=workers, is_start=False)
        elif answer == "11":
            os.system("python3 manage.py flower_events")
        elif answer == "12":
            workers = celery_app.control.inspect().active()
            if workers:
                for worker in workers:
                    print(f" - {worker}")
            else:
                print(" - запущенные воркеры отсутствуют")

        elif answer == "13":
            worker_list = get_workers()
            clearcelery(worker_list)

        elif answer == "14":
            os.system(f"tail -n 0 -f {log_path}workers.log")

        elif answer == "15":
            break

        else:
            print("Такая команда отсутствует")
