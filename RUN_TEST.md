# 🚀 БЫСТРЫЙ ЗАПУСК СИСТЕМЫ

## ✅ Исправления применены (04.06.2026)

Все конструкторы exchange-коннекторов унифицированы.

---

## 📋 Запуск теста

```bash
# Запуск комплексного теста (20 секунд)
python test_system.py
```

### Что тестирует:
- ✅ WebSocket подключения к MEXC, Gate.io, Bybit
- ✅ Получение bid/ask цен
- ✅ Парсинг funding rate (должен быть != 0)
- ✅ Проверка латентности данных
- ✅ Обнаружение арбитражных возможностей

### Ожидаемый результат:
```
🚀 SYSTEM READY FOR PRODUCTION!
Data received: 6/6 (100.0%)
✅ All funding rates are non-zero
```

---

## 🔧 Если возникают ошибки

### Ошибка: "Failed to initialize tester"
**Решение:** Проверьте что все 3 файла обновлены:
- `exchanges/base.py`
- `exchanges/bybit.py`
- `exchanges/mexc.py`
- `exchanges/gate.py`

### Ошибка: "No module named 'exchanges'"
**Решение:** Убедитесь что запускаете из корневой директории проекта

### Ошибка: WebSocket connection failed
**Решение:** Проверьте интернет соединение. Тест использует только публичные данные.

---

## 📊 Структура тестируемых символов

- BTC/USDT
- ETH/USDT

Можно изменить в `test_system.py`:
```python
self.test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
```

---

## 🎯 Следующие шаги

После успешного теста:

1. ✅ Проверьте что funding rate != 0 для всех бирж
2. ✅ Убедитесь что latency < 100ms
3. ✅ Проверьте наличие арбитражных возможностей
4. 🚀 Готово к production!

---

## 📝 Логи

Логи сохраняются в консоль. Для сохранения в файл:
```bash
python test_system.py > test_results.log 2>&1
```

---

**Система готова! 🎉**
