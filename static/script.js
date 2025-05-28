document.addEventListener('DOMContentLoaded', function() {
    const cityInput = document.getElementById('cityInput');
    const suggestionsContainer = document.getElementById('suggestions');
    const weatherResult = document.getElementById('weatherResult');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    
    let debounceTimer;
    
    // Load search stats on page load
    loadSearchStats();
    
    cityInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        
        if (query.length < 2) {
            suggestionsContainer.style.display = 'none';
            return;
        }
        
        debounceTimer = setTimeout(() => {
            fetchSuggestions(query);
        }, 300);
    });
    
    async function fetchSuggestions(query) {
        try {
            const response = await fetch(`/cities/autocomplete?q=${encodeURIComponent(query)}`);
            const cities = await response.json();
            
            suggestionsContainer.innerHTML = '';
            
            if (cities.length > 0) {
                cities.forEach(city => {
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    div.textContent = city.name;
                    div.addEventListener('click', () => {
                        cityInput.value = city.name;
                        suggestionsContainer.style.display = 'none';
                        searchCity(city.name);
                    });
                    suggestionsContainer.appendChild(div);
                });
                suggestionsContainer.style.display = 'block';
            } else {
                suggestionsContainer.style.display = 'none';
            }
        } catch (err) {
            console.error('Ошибка при получении подсказок:', err);
        }
    }
    
    cityInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const city = this.value.trim();
            if (city) {
                searchCity(city);
                suggestionsContainer.style.display = 'none';
            }
        }
    });
    
    // Close suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!cityInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
            suggestionsContainer.style.display = 'none';
        }
    });
    
    async function searchCity(city) {
        try {
            loading.classList.remove('d-none');
            error.classList.add('d-none');
            weatherResult.classList.add('d-none');
            
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `city=${encodeURIComponent(city)}`
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Не удалось получить данные о погоде');
            }
            
            displayWeather(data);
            loadSearchStats();
            
        } catch (err) {
            error.textContent = err.message;
            error.classList.remove('d-none');
        } finally {
            loading.classList.add('d-none');
        }
    }
    
    function displayWeather(data) {
        const weatherResult = document.getElementById('weatherResult');
        weatherResult.classList.remove('d-none');
        
        // Update city name
        weatherResult.querySelector('.city-name').textContent = `${data.city}, ${data.country}`;
        
        // Update current conditions
        weatherResult.querySelector('.temperature').textContent = `${Math.round(data.current.temperature_2m)}°C`;
        weatherResult.querySelector('.humidity').textContent = `Влажность: ${data.current.relative_humidity_2m}%`;
        weatherResult.querySelector('.wind').textContent = `Ветер: ${data.current.wind_speed_10m} км/ч`;
        
        // Update weather description based on weather code
        weatherResult.querySelector('.weather-description').textContent = getWeatherDescription(data.current.weather_code);
        
        // Update hourly forecast
        const hourlyContainer = weatherResult.querySelector('.hourly-container');
        hourlyContainer.innerHTML = '';
        
        for (let i = 0; i < data.hourly.time.length; i++) {
            const time = new Date(data.hourly.time[i]);
            const temp = data.hourly.temperature[i];
            const weatherCode = data.hourly.weather_code[i];
            
            const hourlyItem = document.createElement('div');
            hourlyItem.className = 'hourly-item';
            hourlyItem.innerHTML = `
                <div class="time">${time.getHours()}:00</div>
                <div class="temp">${Math.round(temp)}°C</div>
                <div class="description">${getWeatherDescription(weatherCode)}</div>
            `;
            
            hourlyContainer.appendChild(hourlyItem);
        }
    }
    
    function getWeatherDescription(code) {
        const weatherCodes = {
            0: 'Ясно',
            1: 'Преимущественно ясно',
            2: 'Переменная облачность',
            3: 'Пасмурно',
            45: 'Туман',
            48: 'Изморозь',
            51: 'Легкая морось',
            53: 'Умеренная морось',
            55: 'Сильная морось',
            61: 'Небольшой дождь',
            63: 'Умеренный дождь',
            65: 'Сильный дождь',
            71: 'Небольшой снег',
            73: 'Умеренный снег',
            75: 'Сильный снег',
            77: 'Снежная крупа',
            80: 'Небольшой ливень',
            81: 'Умеренный ливень',
            82: 'Сильный ливень',
            85: 'Небольшой снегопад',
            86: 'Сильный снегопад',
            95: 'Гроза',
            96: 'Гроза с небольшим градом',
            99: 'Гроза с сильным градом'
        };
        
        return weatherCodes[code] || 'Неизвестно';
    }
    
    async function loadSearchStats() {
        try {
            const response = await fetch('/stats');
            const data = await response.json();
            
            const statsContainer = document.getElementById('searchStats');
            statsContainer.innerHTML = '';
            
            data.stats.forEach(stat => {
                const div = document.createElement('div');
                div.className = 'stat-item';
                div.innerHTML = `
                    ${stat.city}
                    <span class="stat-count">${stat.count}</span>
                `;
                div.addEventListener('click', () => {
                    cityInput.value = stat.city;
                    searchCity(stat.city);
                });
                statsContainer.appendChild(div);
            });
        } catch (err) {
            console.error('Ошибка при загрузке статистики:', err);
        }
    }
}); 