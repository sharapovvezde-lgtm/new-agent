# Руководство по развертыванию проекта "AI Presenter"

Это руководство описывает шаги, необходимые для развертывания вашего веб-приложения на удаленном сервере.

### Предварительные требования

1.  **Удаленный сервер:** Любой Linux-сервер (рекомендуется Ubuntu 22.04 LTS) с доступом по SSH. Например, VPS от DigitalOcean, Linode, AWS EC2 и т.д.
2.  **Docker и Docker Compose:** Установленные на вашем сервере.
3.  **Git:** Установленный на сервере для клонирования репозитория.
4.  **Доменное имя (опционально, но рекомендуется):** Домен, который вы можете направить на IP-адрес вашего сервера.

---

### Шаг 1: Подготовка сервера

1.  **Подключитесь к вашему серверу по SSH:**
    ```bash
    ssh username@your_server_ip
    ```

2.  **Установите Docker и Docker Compose (если их нет):**
    ```bash
    # Установка Docker
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Установка Docker Compose (альтернативный способ, если плагин не установился)
    # sudo apt-get install -y docker-compose
    ```
    Добавьте вашего пользователя в группу docker, чтобы избежать использования `sudo` с каждой командой:
    ```bash
    sudo usermod -aG docker $USER
    # Важно: после этого нужно перелогиниться на сервер!
    exit
    ```

3.  **Установите Git:**
    ```bash
    sudo apt-get install -y git
    ```

---

### Шаг 2: Развертывание приложения

1.  **Клонируйте репозиторий вашего проекта:**
    (Замените `your_repository_url` на URL вашего Git-репозитория)
    ```bash
    git clone your_repository_url
    cd your_project_directory # Перейдите в папку с проектом
    ```

2.  **Создайте и настройте файл окружения:**
    Скопируйте пример файла `.env.example` в новый файл `.env`.
    ```bash
    cp .env.example .env
    ```
    Откройте файл `.env` с помощью текстового редактора (например, `nano`) и вставьте ваш ключ API.
    ```bash
    nano .env
    ```
    Содержимое файла должно выглядеть так:
    ```
    OPENROUTER_API_KEY=ваш_ключ_здесь
    ```
    Нажмите `Ctrl+X`, затем `Y` и `Enter`, чтобы сохранить и выйти.

3.  **Соберите и запустите контейнеры:**
    Используйте Docker Compose для сборки образа и запуска сервиса в фоновом режиме (`-d` -- detached).
    ```bash
    docker-compose up --build -d
    ```

4.  **Проверьте, что приложение работает:**
    Вы можете посмотреть логи, чтобы убедиться, что все запустилось без ошибок.
    ```bash
    docker-compose logs -f
    ```
    Если все в порядке, вы должны увидеть сообщения от Uvicorn о том, что сервер запущен. Нажмите `Ctrl+C`, чтобы выйти из логов. Ваше приложение теперь доступно по адресу `http://your_server_ip:8001`.

---

### Шаг 3: Настройка Nginx и HTTPS (Рекомендуется для Production)

Запускать приложение напрямую на порту `8001` небезопасно. Лучшей практикой является использование веб-сервера **Nginx** в качестве обратного прокси (reverse proxy), который будет принимать запросы на стандартные порты 80/443 и перенаправлять их на ваше приложение. Это также позволит легко настроить HTTPS.

1.  **Установите Nginx:**
    ```bash
    sudo apt-get install -y nginx
    ```

2.  **Настройте ваш файрвол:**
    ```bash
    sudo ufw allow 'Nginx Full'
    sudo ufw allow OpenSSH
    sudo ufw enable
    ```

3.  **Создайте конфигурационный файл для вашего сайта:**
    ```bash
    sudo nano /etc/nginx/sites-available/your_domain
    ```
    Вставьте следующую конфигурацию, заменив `your_domain` на ваше доменное имя и `your_server_ip` на IP вашего сервера.
    ```nginx
    server {
        listen 80;
        server_name your_domain www.your_domain;

        location / {
            proxy_pass http://localhost:8001; # Перенаправляем на наше приложение
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```

4.  **Активируйте конфигурацию:**
    ```bash
    sudo ln -s /etc/nginx/sites-available/your_domain /etc/nginx/sites-enabled/
    sudo nginx -t # Проверка синтаксиса
    sudo systemctl restart nginx
    ```

5.  **Настройте HTTPS с помощью Certbot (Let's Encrypt):**
    Это автоматически получит бесплатный SSL-сертификат и настроит Nginx для его использования.
    ```bash
    sudo apt-get install -y certbot python3-certbot-nginx
    sudo certbot --nginx -d your_domain -d www.your_domain
    ```
    Следуйте инструкциям на экране. Certbot автоматически обновит вашу конфигурацию Nginx для HTTPS.

**Поздравляем!** Ваше приложение развернуто, защищено и доступно по адресу `https://your_domain`.

### Управление приложением

*   **Остановить приложение:** `docker-compose down`
*   **Перезапустить приложение:** `docker-compose restart`
*   **Посмотреть логи:** `docker-compose logs -f`
*   **Обновить приложение после изменений в коде:**
    ```bash
    git pull # Скачать последнюю версию кода
    docker-compose up --build -d # Пересобрать и перезапустить
    ```

