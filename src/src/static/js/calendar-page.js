document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const currentMonthElement = document.getElementById('current-month');
    const calendarDaysElement = document.getElementById('calendar-days');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const eventDetailsElement = document.getElementById('event-details');
    const eventDateElement = document.getElementById('event-date');
    const eventsListElement = document.getElementById('events-list');
    const noEventsElement = document.getElementById('no-events');
    const upcomingEventsListElement = document.getElementById('upcoming-events-list');
    const noUpcomingEventsElement = document.getElementById('no-upcoming-events');
    const backToCalendarBtn = document.getElementById('back-to-calendar');
    
    // Modal elements
    const addEventBtn = document.getElementById('add-event-btn');
    const addEventModal = document.getElementById('add-event-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    const cancelBtn = document.querySelector('.cancel-btn');
    const addEventForm = document.getElementById('add-event-form');
    
    // Track current calendar view
    let currentYear = new Date().getFullYear();
    let currentMonth = new Date().getMonth() + 1; // JavaScript months are 0-based
    
    // Initialize the calendar
    initCalendar();
    
    // Event listeners
    prevMonthBtn.addEventListener('click', () => {
        navigateMonth(-1);
    });
    
    nextMonthBtn.addEventListener('click', () => {
        navigateMonth(1);
    });
    
    backToCalendarBtn.addEventListener('click', () => {
        eventDetailsElement.style.display = 'none';
    });
    
    // Modal event listeners
    addEventBtn.addEventListener('click', () => {
        // Set default date to today
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0]; // Format: YYYY-MM-DD
        document.getElementById('event-date-input').value = formattedDate;
        
        // Show modal
        addEventModal.style.display = 'flex';
    });
    
    closeModalBtn.addEventListener('click', () => {
        addEventModal.style.display = 'none';
    });
    
    cancelBtn.addEventListener('click', () => {
        addEventModal.style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        if (event.target === addEventModal) {
            addEventModal.style.display = 'none';
        }
    });
    
    // Form submission handler
    addEventForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const eventName = document.getElementById('event-name').value;
        const eventDate = document.getElementById('event-date-input').value;
        const eventTime = document.getElementById('event-time').value;
        
        if (!eventName || !eventDate) {
            alert('Please fill out the required fields.');
            return;
        }
        
        try {
            const response = await fetch('/api/calendar/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    event_name: eventName,
                    date_str: eventDate,
                    time_str: eventTime
                })
            });
            
            if (response.ok) {
                // Clear form
                addEventForm.reset();
                
                // Close modal
                addEventModal.style.display = 'none';
                
                // Refresh calendar
                fetchMonthData(currentYear, currentMonth);
                
                // Also refresh upcoming events
                fetchUpcomingEvents();
                
                alert('Event added successfully!');
            } else {
                const data = await response.json();
                alert(`Error: ${data.error || 'Failed to add event'}`);
            }
        } catch (error) {
            console.error('Error adding event:', error);
            alert('An error occurred while adding the event. Please try again.');
        }
    });
    
    // Functions
    async function initCalendar() {
        try {
            await fetchMonthData(currentYear, currentMonth);
            await fetchUpcomingEvents();
        } catch (error) {
            console.error('Error initializing calendar:', error);
            showErrorMessage('Failed to load calendar data. Please try refreshing the page.');
        }
    }
    
    function navigateMonth(direction) {
        // Calculate new month
        let newMonth = currentMonth + direction;
        let newYear = currentYear;
        
        if (newMonth > 12) {
            newMonth = 1;
            newYear++;
        } else if (newMonth < 1) {
            newMonth = 12;
            newYear--;
        }
        
        // Update current month and year
        currentMonth = newMonth;
        currentYear = newYear;
        
        // Fetch and display new month
        fetchMonthData(currentYear, currentMonth);
    }
    
    async function fetchMonthData(year, month) {
        try {
            const response = await fetch(`/api/calendar/month?year=${year}&month=${month}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.calendar) {
                displayCalendar(data.calendar);
            } else {
                throw new Error('Invalid calendar data received');
            }
        } catch (error) {
            console.error('Error fetching calendar month:', error);
            showErrorMessage('Error loading calendar. Please try again.');
        }
    }
    
    async function fetchUpcomingEvents() {
        try {
            const response = await fetch('/api/calendar/events/upcoming');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            updateUpcomingEvents(data.events);
        } catch (error) {
            console.error('Error fetching upcoming events:', error);
            showErrorMessage('Error loading upcoming events. Please try again.');
        }
    }
    
    function displayCalendar(calendarData) {
        // Set current month/year title
        currentMonthElement.textContent = `${calendarData.month_name} ${calendarData.year}`;
        
        // Clear existing calendar days
        calendarDaysElement.innerHTML = '';
        
        // Add calendar days
        calendarData.days.forEach(day => {
            const dayElement = document.createElement('div');
            dayElement.className = 'calendar-day';
            
            // Add additional classes based on day properties
            if (!day.is_current_month) {
                dayElement.classList.add('other-month');
            }
            if (day.is_today) {
                dayElement.classList.add('current-day');
            }
            if (day.has_events) {
                dayElement.classList.add('has-events');
            }
            
            // Add day number
            const dayNumber = document.createElement('div');
            dayNumber.className = 'day-number';
            dayNumber.textContent = day.day;
            dayElement.appendChild(dayNumber);
            
            // Add event indicator if there are events
            if (day.has_events) {
                const eventIndicator = document.createElement('div');
                eventIndicator.className = 'event-indicator';
                dayElement.appendChild(eventIndicator);
                
                // Add event preview if there are events
                if (day.events && day.events.length > 0) {
                    const eventPreview = document.createElement('div');
                    eventPreview.className = 'event-preview';
                    eventPreview.textContent = day.events[0].event;
                    dayElement.appendChild(eventPreview);
                    
                    // Show count if more than one event
                    if (day.events.length > 1) {
                        const eventCount = document.createElement('div');
                        eventCount.className = 'event-count';
                        eventCount.textContent = `+${day.events.length - 1} more`;
                        dayElement.appendChild(eventCount);
                    }
                }
            }
            
            // Add click event to show events for this day
            dayElement.addEventListener('click', () => {
                showEventsForDay(day);
            });
            
            // Add day to calendar
            calendarDaysElement.appendChild(dayElement);
        });
    }
    
    function showEventsForDay(day) {
        // Format date nicely
        const dateObj = new Date(day.date);
        const formattedDate = dateObj.toLocaleDateString('en-US', { 
            weekday: 'long', 
            month: 'long', 
            day: 'numeric',
            year: 'numeric'
        });
        
        // Set date in header
        eventDateElement.textContent = formattedDate;
        
        // Clear events list
        eventsListElement.innerHTML = '';
        
        // Show event details section
        eventDetailsElement.style.display = 'block';
        
        // If no events, show the "no events" message
        if (!day.events || day.events.length === 0) {
            eventsListElement.style.display = 'none';
            noEventsElement.style.display = 'block';
            return;
        }
        
        // Otherwise, show the events and hide the "no events" message
        eventsListElement.style.display = 'block';
        noEventsElement.style.display = 'none';
        
        // Add events to the list
        day.events.forEach(event => {
            const eventElement = document.createElement('div');
            eventElement.className = 'event-item';
            
            // Create HTML for the event
            eventElement.innerHTML = `
                ${event.time ? `<div class="event-time">${event.time}</div>` : ''}
                <div class="event-title">${event.event}</div>
            `;
            
            eventsListElement.appendChild(eventElement);
        });
    }
    
    function updateUpcomingEvents(events) {
        // Clear existing events
        upcomingEventsListElement.innerHTML = '';
        
        // If no events, show the "no events" message
        if (!events || events.length === 0) {
            upcomingEventsListElement.style.display = 'none';
            noUpcomingEventsElement.style.display = 'block';
            return;
        }
        
        // Otherwise, show the events and hide the "no events" message
        upcomingEventsListElement.style.display = 'block';
        noUpcomingEventsElement.style.display = 'none';
        
        // Add events to the list
        events.forEach(event => {
            const eventElement = document.createElement('div');
            eventElement.className = 'upcoming-event';
            
            // Format date in a more readable format
            const dateObj = event.date ? new Date(event.date) : null;
            const formattedDate = dateObj ? 
                dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) : 
                'No date specified';
            
            // Create HTML for the event
            eventElement.innerHTML = `
                <div class="upcoming-event-date">${formattedDate}</div>
                <div class="upcoming-event-title">${event.event}</div>
                ${event.time ? `<div class="upcoming-event-time">${event.time}</div>` : ''}
            `;
            
            upcomingEventsListElement.appendChild(eventElement);
        });
    }
    
    function showErrorMessage(message) {
        // Create error message element
        const errorMessageElement = document.createElement('div');
        errorMessageElement.className = 'error-message';
        errorMessageElement.textContent = message;
        
        // Append to body
        document.body.appendChild(errorMessageElement);
        
        // Remove after 5 seconds
        setTimeout(() => {
            document.body.removeChild(errorMessageElement);
        }, 5000);
    }
}); 