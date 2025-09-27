## Установка

### Клонируем проект

```bash
sudo git clone -b production https://github.com/cloudsucker/kinoliba.git /opt/kinoliba
cd /opt/kinoliba
```

### Делаем скрипт исполняемым

```bash
# Меняем владельца папки на своего пользователя
sudo chown -R $(whoami):$(whoami) /opt/kinoliba
chmod +x deploy.sh
```

### Первый запуск и настройка

```bash
./deploy.sh
```
