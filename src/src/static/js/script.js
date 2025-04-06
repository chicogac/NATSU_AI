document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded - initializing application");
    
    // DOM Elements
    const buddyDot = document.getElementById('buddy-dot');
    const responseText = document.getElementById('response-text');
    const startListeningBtn = document.getElementById('start-listening');
    const textInput = document.getElementById('text-input');
    const sendTextBtn = document.getElementById('send-text');
    
    // Reminder elements
    const reminderButton = document.getElementById('reminders-button');
    const reminderBadge = document.getElementById('reminder-badge');
    const remindersContainer = document.getElementById('reminders-container');
    const closeRemindersBtn = document.getElementById('close-reminders');
    const remindersList = document.getElementById('reminders-list');
    const noReminders = document.getElementById('no-reminders');
    
    // Verify critical DOM elements
    console.log("Verifying DOM elements:");
    console.log("- reminderButton:", reminderButton ? "Found" : "NOT FOUND");
    console.log("- remindersContainer:", remindersContainer ? "Found" : "NOT FOUND");
    console.log("- closeRemindersBtn:", closeRemindersBtn ? "Found" : "NOT FOUND");
    console.log("- remindersList:", remindersList ? "Found" : "NOT FOUND");
    
    // Move reminders container to body to avoid nesting issues
    if (remindersContainer && document.body) {
        document.body.appendChild(remindersContainer);
        console.log("Moved reminders container to document body");
    }
    
    // Initialize reminders
    let activeReminders = [];
    let reminderNotificationShown = false;
    
    // Check for reminders on page load and every 5 minutes
    checkForReminders();
    setInterval(checkForReminders, 5 * 60 * 1000);
    
    // Function to check for reminders
    async function checkForReminders() {
        try {
            console.log("Fetching reminders from server...");
            const response = await fetch('/api/reminders');
            
            if (!response.ok) {
                console.error('Failed to fetch reminders:', response.status);
                return;
            }
            
            const data = await response.json();
            console.log("Received reminders response:", data);
            
            activeReminders = data.reminders || [];
            
            // Filter only today's events for the badge and auto-popup
            const todayReminders = activeReminders.filter(reminder => reminder.is_today === true);
            
            console.log('Reminder check:', 
                       `Found ${activeReminders.length} active reminders (${todayReminders.length} for today)`);
            
            // Update badge with TODAY'S reminders count only
            if (todayReminders.length > 0) {
                reminderBadge.textContent = todayReminders.length;
                reminderBadge.style.display = 'flex';
                
                // Auto-show reminders on page load if there are today's events
                if (!reminderNotificationShown) {
                    reminderNotificationShown = true;
                    remindersContainer.style.display = 'block';
                    
                    // Auto-hide after 10 seconds
                    setTimeout(() => {
                        remindersContainer.style.display = 'none';
                    }, 10000);
                }
            } else {
                reminderBadge.style.display = 'none';
            }
            
            // Pre-populate the reminders list
            updateRemindersList();
            
        } catch (error) {
            console.error('Error checking reminders:', error);
        }
    }
    
    // Function to update the reminders list
    function updateRemindersList() {
        console.log("Updating reminders list with:", activeReminders);
        remindersList.innerHTML = '';
        
        if (activeReminders.length === 0) {
            console.log("No active reminders found, showing empty state");
            noReminders.style.display = 'block';
            noReminders.textContent = 'No events scheduled for today or tomorrow';
            return;
        }
        
        console.log(`Found ${activeReminders.length} reminders to display`);
        noReminders.style.display = 'none';
        
        // Sort reminders to put today's events first
        const sortedReminders = [...activeReminders].sort((a, b) => {
            // First sort by today vs tomorrow
            if (a.is_today && !b.is_today) return -1;
            if (!a.is_today && b.is_today) return 1;
            
            // Then sort by time if both are the same day
            if (a.time && b.time) {
                return a.time.localeCompare(b.time);
            }
            
            // Put events with time before events without time
            if (a.time && !b.time) return -1;
            if (!a.time && b.time) return 1;
            
            // If nothing else to sort by, sort by event name
            return a.event.localeCompare(b.event);
        });
        
        // Add heading for today's events if any
        const todayReminders = sortedReminders.filter(r => r.is_today);
        if (todayReminders.length > 0) {
            const todayHeading = document.createElement('div');
            todayHeading.className = 'reminders-section-heading';
            todayHeading.textContent = "Today's Events";
            remindersList.appendChild(todayHeading);
        }
        
        // Add today's events
        todayReminders.forEach((reminder, index) => {
            addReminderItem(reminder, index);
        });
        
        // Add heading for tomorrow's events if any
        const tomorrowReminders = sortedReminders.filter(r => !r.is_today);
        if (tomorrowReminders.length > 0) {
            const tomorrowHeading = document.createElement('div');
            tomorrowHeading.className = 'reminders-section-heading';
            tomorrowHeading.textContent = "Tomorrow's Events";
            remindersList.appendChild(tomorrowHeading);
            
            // Add tomorrow's events
            tomorrowReminders.forEach((reminder, index) => {
                addReminderItem(reminder, index + todayReminders.length);
            });
        }
        
        function addReminderItem(reminder, index) {
            const reminderItem = document.createElement('div');
            reminderItem.className = `reminder-item${reminder.is_today ? ' today' : ''}`;
            
            // Format the time if available
            let timeText = '';
            if (reminder.time) {
                try {
                    // Convert 24-hour format to 12-hour format if needed
                    const timeParts = reminder.time.split(':');
                    const hour = parseInt(timeParts[0]);
                    const minute = timeParts[1];
                    const ampm = hour >= 12 ? 'PM' : 'AM';
                    const hour12 = hour % 12 || 12;
                    timeText = `${hour12}:${minute} ${ampm}`;
                } catch (e) {
                    timeText = reminder.time;
                }
            }
            
            reminderItem.innerHTML = `
                <div class="reminder-content">
                    <div class="reminder-title">${reminder.event}</div>
                    <div class="reminder-time">${timeText ? timeText : 'All day'}</div>
                </div>
                <div class="reminder-actions">
                    <button class="dismiss-reminder" data-index="${index}" title="Dismiss">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            `;
            
            // Add click event to dismiss button
            const dismissBtn = reminderItem.querySelector('.dismiss-reminder');
            dismissBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                dismissReminder(index);
            });
            
            remindersList.appendChild(reminderItem);
        }
    }
    
    // Function to dismiss a reminder
    function dismissReminder(index) {
        if (index >= 0 && index < activeReminders.length) {
            activeReminders.splice(index, 1);
            updateRemindersList();
            
            // Update badge
            if (activeReminders.length > 0) {
                reminderBadge.textContent = activeReminders.length;
            } else {
                reminderBadge.style.display = 'none';
            }
        }
    }
    
    // Toggle reminders container when reminder button is clicked
    if (reminderButton) {
        console.log("Setting up reminder button click handler");
        reminderButton.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent event bubbling
            
            console.log("Reminder button clicked!");
            
            if (!remindersContainer) {
                console.error("Reminders container not found!");
                return;
            }
            
            // Force reminders container to be visible
            remindersContainer.style.display = 'block';
            remindersContainer.style.zIndex = '1001'; // Ensure it's on top
            
            // Reset any positioning that might have moved it off-screen
            remindersContainer.style.left = 'auto';
            remindersContainer.style.right = '20px';
            remindersContainer.style.transform = 'none';
            
            // Update the reminders list to ensure fresh data
            updateRemindersList();
            
            // Check if it's visible
            console.log("Reminders container display:", remindersContainer.style.display);
            console.log("Reminders container position right:", remindersContainer.style.right);
            console.log("Reminders container position left:", remindersContainer.style.left);
        });
    } else {
        console.error("Reminder button element not found!");
    }
    
    // Close reminders when close button is clicked
    if (closeRemindersBtn) {
        console.log("Setting up close reminders button handler");
        closeRemindersBtn.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent event bubbling
            console.log("Close reminders button clicked");
            remindersContainer.style.display = 'none';
        });
    } else {
        console.error("Close reminders button not found!");
    }
    
    // Calendar button click handler
    const calendarButton = document.getElementById('calendar-button');
    if (calendarButton) {
        calendarButton.addEventListener('click', () => {
            window.location.href = '/calendar';
        });
    }
    
    // Health button click handler
    const healthButton = document.getElementById('health-button');
    if (healthButton) {
        healthButton.addEventListener('click', () => {
            window.location.href = '/health';
        });
    }
    
    // Display area elements
    const displayArea = document.getElementById('display-area');
    const placeholderText = document.querySelector('.placeholder-text');
    
    // News elements
    const newsContent = document.getElementById('news-content');
    const newsHeadlines = document.getElementById('news-headlines');
    const articleDetails = document.getElementById('article-details');
    const articleTitle = document.getElementById('article-title');
    const articleMeta = document.getElementById('article-meta');
    const articleContent = document.getElementById('article-content');
    const backToHeadlinesBtn = document.getElementById('back-to-headlines');
    const articleAnalysis = document.getElementById('article-analysis');
    
    // Calendar elements
    const calendarContent = document.getElementById('calendar-content');
    const currentMonthDisplay = document.getElementById('current-month');
    const calendarDays = document.getElementById('calendar-days');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const eventDetails = document.getElementById('event-details');
    const eventDate = document.getElementById('event-date');
    const eventsList = document.getElementById('events-list');
    const noEvents = document.getElementById('no-events');
    const upcomingEventsList = document.getElementById('upcoming-events-list');
    const noUpcomingEvents = document.getElementById('no-upcoming-events');
    const backToCalendarBtn = document.getElementById('back-to-calendar');
    
    // Story content elements - create if they don't exist yet
    if (!document.getElementById('story-content')) {
        // Create story content container
        const storyContent = document.createElement('div');
        storyContent.id = 'story-content';
        storyContent.className = 'content-section';
        storyContent.style.display = 'none';
        
        // Create story images container
        const storyImagesContainer = document.createElement('div');
        storyImagesContainer.id = 'story-images-container';
        storyImagesContainer.className = 'story-images-container';
        
        // Create back button similar to the news one
        const backBtn = document.createElement('button');
        backBtn.id = 'back-from-story';
        backBtn.className = 'back-button';
        backBtn.textContent = '← Back';
        
        // Add elements to DOM
        storyContent.appendChild(backBtn);
        storyContent.appendChild(storyImagesContainer);
        displayArea.appendChild(storyContent);
        
        // Add event listener to back button
        backBtn.addEventListener('click', () => {
            resetDisplayArea();
        });
    }
    
    const storyContent = document.getElementById('story-content');
    const storyImagesContainer = document.getElementById('story-images-container');
    
    // News data storage
    let currentNewsData = null;
    let currentArticleId = null;
    
    // Calendar data storage
    let currentCalendarData = null;
    let currentCalendarYear = new Date().getFullYear();
    let currentCalendarMonth = new Date().getMonth() + 1; // JavaScript months are 0-based
    
    // For client-side recording
    let mediaRecorder;
    let audioChunks = [];
    
    // For audio playback
    let isPlaying = false;
    let audioElement = new Audio();
    
    // For tracking active typing animation
    let activeTypingInterval = null;
    let isTypingActive = false;
    
    // State management
    let isProcessing = false;

    // Functions to display messages
    function displayUserMessage(message) {
        const responseText = document.getElementById('response-text');
        responseText.innerHTML = `<div class="user-message">You: ${message}</div>`;
    }

    function displayAIResponse(response) {
        // Start the typing animation for the AI response
        speakAndTypeText(response, document.getElementById('response-text'));
    }

    // Function to detect and handle navigation commands
    function handleNavigationCommand(message) {
        // Convert message to lowercase for easier matching
        const command = message.toLowerCase().trim();
        
        // Define common navigation patterns
        const backPatterns = [
            /go\s+back/i,
            /back/i,
            /return/i,
            /previous/i
        ];
        
        const exitPatterns = [
            /exit/i,
            /close/i,
            /hide/i,
            /dismiss/i
        ];
        
        const homePatterns = [
            /home/i,
            /main/i,
            /landing/i,
            /start/i,
            /beginning/i
        ];
        
        const calendarPatterns = [
            /calendar/i,
            /schedule/i,
            /events/i,
            /agenda/i
        ];
        
        const newsPatterns = [
            /news/i,
            /headlines/i,
            /articles/i
        ];
        
        // Determine current application state
        const isArticleOpen = articleDetails && articleDetails.style.display !== 'none';
        const isNewsOpen = newsContent && newsContent.style.display !== 'none' && !isArticleOpen;
        const isCalendarOpen = calendarContent && calendarContent.style.display !== 'none';
        const isEventDetailsOpen = eventDetails && eventDetails.style.display !== 'none';
        
        // Check for back/exit commands first
        const isBackCommand = backPatterns.some(pattern => pattern.test(command));
        const isExitCommand = exitPatterns.some(pattern => pattern.test(command)) && 
                             command.includes('this');
        
        if (isBackCommand || isExitCommand) {
            // Cancel any active typing
            cancelActiveTyping();
            
            // Handle navigation based on current state
            if (isArticleOpen) {
                // Back from article to news headlines
                articleDetails.style.display = 'none';
                restoreNewsHeadlinesLayout();
                responseText.textContent = "Going back to news headlines.";
                return true;
            } else if (isNewsOpen) {
                // Back from news to home
                resetDisplayArea();
                responseText.textContent = "Returning to main screen.";
                return true;
            } else if (isEventDetailsOpen) {
                // Back from event details to calendar
                eventDetails.style.display = 'none';
                responseText.textContent = "Going back to calendar view.";
                return true;
            } else if (isCalendarOpen) {
                // Back from calendar to home
                resetDisplayArea();
                responseText.textContent = "Returning to main screen.";
                return true;
            }
        }
        
        // Check for specific destination commands
        
        // Go to calendar
        if (calendarPatterns.some(pattern => pattern.test(command)) && 
            (command.includes('go to') || command.includes('show') || command.includes('open'))) {
            // Redirect to calendar page
            window.location.href = '/calendar';
            return true;
        }
        
        // Go to news/headlines
        if (newsPatterns.some(pattern => pattern.test(command)) && 
            (command.includes('go to') || command.includes('show') || command.includes('open'))) {
            // Handle like a news request - let the regular flow continue
            return false;
        }
        
        // Go to home/main screen
        if (homePatterns.some(pattern => pattern.test(command)) && 
            (command.includes('go to') || command.includes('go back to') || 
             command.includes('return to') || command.includes('show'))) {
            resetDisplayArea();
            responseText.textContent = "Back to main screen.";
            return true;
        }
        
        // If no navigation command matched
        return false;
    }

    // Function to send text input to the backend
    async function sendTextMessage(message) {
        try {
            setProcessingState(true);
            
            // First check if this is a navigation command
            if (handleNavigationCommand(message)) {
                // Clear the input field
                document.getElementById('text-input').value = '';
                
                // Display user message
                displayUserMessage(message);
                
                // If it was a navigation command, we're done
                setProcessingState(false);
                return;
            }
            
            // Check if user is asking about a specific article by number after headlines have been shown
            if (currentNewsData && currentNewsData.articles && currentNewsData.articles.length > 0) {
                // Look for patterns like "tell me about article 2" or "expand on article 3" or "show article 1" or simply "2"
                const articlePatterns = [
                    /article\s*(\d+)/i,             // "article 2"
                    /show\s*(?:me\s*)?(?:article\s*)?(\d+)/i,  // "show me 2" or "show article 2"
                    /(?:tell|talk|more)\s*(?:me\s*)?(?:about\s*)?(?:article\s*)?(\d+)/i, // "tell me about article 2"
                    /(?:expand|explain|open|read)\s*(?:on\s*)?(?:article\s*)?(\d+)/i,    // "expand on article 2"
                    /^(\d+)$/                        // Just the number "2"
                ];
                
                let articleId = null;
                
                // Try to match the patterns
                for (const pattern of articlePatterns) {
                    const match = message.match(pattern);
                    if (match && match[1]) {
                        articleId = parseInt(match[1]);
                        break;
                    }
                }
                
                // If we found a valid article ID that exists in our data, load it directly
                if (articleId && articleId > 0 && articleId <= currentNewsData.articles.length) {
                    // Update response to acknowledge the request
                    responseText.textContent = `Opening article ${articleId} for you...`;
                    
                    // Clear the input field
                    document.getElementById('text-input').value = '';
                    
                    // Display user message
                    displayUserMessage(message);
                    
                    // Load the article details directly - don't speak since we're coming from a text message
                    loadArticleDetails(articleId, false);
                    return; // Exit early - no need to make the API call
                }
                
                // Also check if the user mentioned an article by title
                if (message.length > 3) { // Only check for non-trivial messages
                    for (const article of currentNewsData.articles) {
                        // Check if the message contains a significant portion of the article title
                        const title = article.title.toLowerCase();
                        const messageLower = message.toLowerCase();
                        
                        // Check if the message contains a substantial part of the title (at least 5 chars)
                        // or if the message includes distinctive keywords from the title
                        if ((title.length > 5 && messageLower.includes(title.substring(0, Math.min(title.length, 10)))) ||
                            (title.split(' ').some(word => word.length > 4 && messageLower.includes(word.toLowerCase())))) {
                            responseText.textContent = `Opening article about "${article.title}"...`;
                            
                            // Clear the input field
                            document.getElementById('text-input').value = '';
                            
                            // Display user message
                            displayUserMessage(message);
                            
                            // Load article but don't speak since we're coming from a text message
                            loadArticleDetails(article.id, false);
                            return;
                        }
                    }
                }
            }
            
            // If an article is currently open, check if the message is asking about it
            if (currentArticleId !== null && articleDetails.style.display !== 'none') {
                // The user is likely asking a question about the current article
                // Let's route this question to the article analysis function
                
                responseText.textContent = `Analyzing article ${currentArticleId} with your question...`;
                
                // Use the same endpoint as the article question input
                const response = await fetch('/api/news/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        article_id: currentArticleId,
                        question: message
                    }),
                });
                
                const data = await response.json();
                
                if (response.ok && data.success) {
                    // Display response in the main response area 
                    speakAndTypeText(data.analysis, responseText);
                    
                    // Also update the article analysis section
                    articleAnalysis.textContent = data.analysis;
                    
                    // Play audio if available
                    if (data.audio_url) {
                        audioElement = new Audio(data.audio_url);
                        audioElement.play().catch(error => {
                            console.error('Failed to play analysis audio:', error);
                        });
                    }
                    
                    return; // Exit early
                }
                // If analysis fails, continue with regular chat flow
            }
            
            // Continue with normal chat flow
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`HTTP error! status: ${response.status}, details:`, errorText);
                throw new Error(`Server error: ${response.status} - ${response.statusText}`);
            }
            
            let data;
            try {
                data = await response.json();
                console.log("API response received:", data);
                
                if (!data || typeof data !== 'object') {
                    throw new Error('Invalid response format: Expected JSON object');
                }
            } catch (parseError) {
                console.error("JSON parse error:", parseError);
                throw new Error(`Failed to parse server response: ${parseError.message}`);
            }
            
            // Clear the input field
            document.getElementById('text-input').value = '';
            
            // Display user message
            displayUserMessage(message);
            
            // Check if we have calendar data
            if (data.calendar_data && data.calendar_data.has_calendar) {
                handleCalendarResponse(data);
            }
            // Check if we have news data
            else if (data.news_data && data.news_data.has_news) {
                handleNewsResponse(data);
            }
            // If response has story data
            else if (data.story_data && data.story_data.has_story_data) {
                console.log("Story data detected:", data.story_data);
                
                // Display the text response in the chat area
                if (typeof data.response === 'string') {
                    displayAIResponse(data.response);
                }
                
                // Use the same direct approach that worked in the test script
                if (data.story_data.media_ids && Array.isArray(data.story_data.media_ids) && data.story_data.media_ids.length > 0) {
                    console.log("Displaying story images using direct method:", data.story_data.media_ids);
                    displayStoryImagesDirectly(data.story_data.media_ids);
                } else {
                    console.warn("No media IDs found in story data");
                }
            }
            // Otherwise, just display the response text
            else {
                console.log("Standard text response received:", data);
                displayAIResponse(data.response);
            }
            
            return data;
        } catch (error) {
            console.error('Error sending message:', error);
            showErrorMessage("Error sending message. Please try again.");
            setProcessingState(false);
        }
    }

    // Function to handle calendar response
    function handleCalendarResponse(data) {
        // Reset display area to ensure clean state
        resetDisplayArea();
        
        // Get the calendar container
        const calendarContent = document.getElementById('calendar-content');
        
        // Show the calendar content
        calendarContent.style.display = 'flex';
        
        // Display the calendar data
        if (data.calendar_data && data.calendar_data.calendar) {
            displayCalendar(data.calendar_data.calendar);
        }
        
        // Display upcoming events
        if (data.calendar_data && data.calendar_data.upcoming_events) {
            updateUpcomingEvents(data.calendar_data.upcoming_events);
        }
        
        // Speak and display the response - do this only ONCE
        const responseText = document.getElementById('response-text');
        speakAndTypeText(data.response, responseText);
    }
    
    // Function to display calendar days
    function displayCalendar(calendarData) {
        const currentMonthElement = document.getElementById('current-month');
        const calendarDaysElement = document.getElementById('calendar-days');
        const prevMonthBtn = document.getElementById('prev-month');
        const nextMonthBtn = document.getElementById('next-month');
        
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
                }
            }
            
            // Add click event to show events for this day
            dayElement.addEventListener('click', () => {
                showEventsForDay(day);
            });
            
            // Add day to calendar
            calendarDaysElement.appendChild(dayElement);
        });
        
        // Clean up old listeners using cloneNode technique
        const prevClone = prevMonthBtn.cloneNode(true);
        const nextClone = nextMonthBtn.cloneNode(true);
        
        // Replace the old buttons with the clones (removes all event listeners)
        prevMonthBtn.parentNode.replaceChild(prevClone, prevMonthBtn);
        nextMonthBtn.parentNode.replaceChild(nextClone, nextMonthBtn);
        
        // Add new event listeners to the cloned buttons
        prevClone.addEventListener('click', () => navigateMonth(-1));
        nextClone.addEventListener('click', () => navigateMonth(1));
    }
    
    // Function to update upcoming events list
    function updateUpcomingEvents(events) {
        const upcomingEventsListElement = document.getElementById('upcoming-events-list');
        const noUpcomingEventsElement = document.getElementById('no-upcoming-events');
        
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
    
    // Function to show events for a specific day
    function showEventsForDay(day) {
        const eventDetailsElement = document.getElementById('event-details');
        const eventsListElement = document.getElementById('events-list');
        const noEventsElement = document.getElementById('no-events');
        const eventDateElement = document.getElementById('event-date');
        
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
        
        // Add event listener to back button using the clone technique
        const backBtnClone = backToCalendarBtn.cloneNode(true);
        backToCalendarBtn.parentNode.replaceChild(backBtnClone, backToCalendarBtn);
        backBtnClone.addEventListener('click', () => {
            eventDetailsElement.style.display = 'none';
        });
    }
    
    // Calendar navigation functions
    function navigateMonth(direction) {
        // Get current month display
        const currentMonthElement = document.getElementById('current-month');
        const currentText = currentMonthElement.textContent; // Format: "Month Year"
        
        // Parse month and year
        const [monthName, yearStr] = currentText.split(' ');
        const year = parseInt(yearStr);
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                        'July', 'August', 'September', 'October', 'November', 'December'];
        const month = months.indexOf(monthName) + 1; // Convert to 1-12 format
        
        // Calculate new month/year
        let newMonth = month + direction;
        let newYear = year;
        
        if (newMonth < 1) {
            newMonth = 12;
            newYear--;
        } else if (newMonth > 12) {
            newMonth = 1;
            newYear++;
        }
        
        // Fetch the new month's calendar data
        fetchCalendarMonth(newYear, newMonth);
    }
    
    // Function to fetch calendar month data
    async function fetchCalendarMonth(year, month) {
        try {
            const response = await fetch(`/api/calendar/month?year=${year}&month=${month}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.calendar) {
                // Display the new calendar
                displayCalendar(data.calendar);
                
                // Also fetch updated upcoming events
                const eventsResponse = await fetch('/api/calendar/events/upcoming');
                if (eventsResponse.ok) {
                    const eventsData = await eventsResponse.json();
                    updateUpcomingEvents(eventsData.events);
                }
            }
        } catch (error) {
            console.error('Error fetching calendar month:', error);
            showErrorMessage("Error loading calendar. Please try again.");
        }
    }

    // Function to handle news response
    function handleNewsResponse(data) {
        // Store news data
        currentNewsData = data.news_data;
        
        // Hide placeholder
        placeholderText.style.display = 'none';
        
        // Hide any other content (like calendar)
        calendarContent.style.display = 'none';
        
        // Clear existing headlines
        newsHeadlines.innerHTML = '';
        
        // Format headlines for display with proper structure
        let headlineSummary = "Here are today's top headlines:\n\n";
        
        // Add each headline with proper formatting
        if (data.news_data && data.news_data.articles) {
            data.news_data.articles.forEach((article, index) => {
                // Add to the formatted text with proper line breaks
                headlineSummary += `${article.id}. ${article.title}\n\n`;
                
                const headlineEl = document.createElement('div');
                headlineEl.className = 'news-headline';
                headlineEl.dataset.articleId = article.id;
                
                // Create newspaper header element
                const paperHeader = document.createElement('div');
                paperHeader.className = 'paper-header';
                paperHeader.style.fontFamily = 'Times New Roman, serif';
                paperHeader.style.textAlign = 'center';
                paperHeader.style.color = '#fff';
                paperHeader.style.fontSize = '0.7rem';
                paperHeader.style.textTransform = 'uppercase';
                paperHeader.style.letterSpacing = '1px';
                paperHeader.style.padding = '2px 0';
                paperHeader.textContent = 'Daily News';
                headlineEl.appendChild(paperHeader);
                
                // Create article number circle
                const articleNumber = document.createElement('div');
                articleNumber.className = 'article-number';
                articleNumber.textContent = article.id;
                headlineEl.appendChild(articleNumber);
                
                // Create article image if available
                if (article.image_url) {
                    const imageContainer = document.createElement('div');
                    imageContainer.className = 'headline-image-container';
                    
                    const headlineImage = document.createElement('img');
                    headlineImage.className = 'headline-image';
                    headlineImage.src = article.image_url;
                    headlineImage.alt = article.title;
                    headlineImage.onerror = function() {
                        // If image fails to load, add a class to the container to show default styling
                        imageContainer.classList.add('image-fallback');
                        this.style.display = 'none';
                    };
                    
                    imageContainer.appendChild(headlineImage);
                    headlineEl.appendChild(imageContainer);
                }
                
                // Create article title
                const headlineTitle = document.createElement('div');
                headlineTitle.className = 'headline-title';
                headlineTitle.textContent = article.title;
                headlineEl.appendChild(headlineTitle);
                
                // Create source info
                const headlineSource = document.createElement('div');
                headlineSource.className = 'headline-source';
                headlineSource.textContent = `Source: ${article.source || 'Unknown'}`;
                headlineEl.appendChild(headlineSource);
                
                // Create date info if available
                if (article.pubDate) {
                    const headlineDate = document.createElement('div');
                    headlineDate.className = 'headline-date';
                    // Format date if possible
                    try {
                        const date = new Date(article.pubDate);
                        headlineDate.textContent = date.toLocaleDateString();
                    } catch (e) {
                        headlineDate.textContent = article.pubDate;
                    }
                    headlineEl.appendChild(headlineDate);
                }
                
                // Create description if available
                if (article.description) {
                    const headlineDesc = document.createElement('div');
                    headlineDesc.className = 'headline-description';
                    headlineDesc.textContent = article.description.substring(0, 140) + '...';
                    headlineEl.appendChild(headlineDesc);
                }
                
                headlineEl.addEventListener('click', () => {
                    // When directly clicking on an article, we should speak (shouldSpeak = true)
                    loadArticleDetails(article.id, true);
                });
                
                newsHeadlines.appendChild(headlineEl);
            });
            
            // Display formatted text in the response area with proper line breaks
            responseText.innerHTML = headlineSummary.replace(/\n/g, '<br>');
            
            // Use speakAndTypeText to speak the headlines
            speakAndTypeText(headlineSummary, responseText);
            
            // Store the original layout
            saveNewsHeadlinesLayout();
            
            // Show news content in display area
            newsContent.style.display = 'block';
            newsHeadlines.style.display = 'flex';  // Ensure correct display property
            
            // Hide article details
            articleDetails.style.display = 'none';
        }
        
        setProcessingState(false);
    }
    
    // Function to save the original layout of news headlines
    function saveNewsHeadlinesLayout() {
        // Save the original display property
        newsHeadlines.dataset.originalDisplay = 'flex';
        
        // Save the original style properties of the container
        const style = window.getComputedStyle(newsHeadlines);
        newsHeadlines.dataset.originalFlexWrap = style.flexWrap;
        newsHeadlines.dataset.originalJustifyContent = style.justifyContent;
        newsHeadlines.dataset.originalGap = style.gap;
    }
    
    // Function to restore the original layout of news headlines
    function restoreNewsHeadlinesLayout() {
        // Restore the original display property
        newsHeadlines.style.display = newsHeadlines.dataset.originalDisplay || 'flex';
        
        // Restore the original layout properties
        newsHeadlines.style.flexWrap = newsHeadlines.dataset.originalFlexWrap || 'wrap';
        newsHeadlines.style.justifyContent = newsHeadlines.dataset.originalJustifyContent || 'center';
        newsHeadlines.style.gap = newsHeadlines.dataset.originalGap || '20px';
        
        // Make sure headlines are visible
        newsContent.style.display = 'block';
    }
    
    // Function to speak text and type simultaneously
    async function speakAndTypeText(text, element) {
        try {
            // Cancel any existing typing animation first
            cancelActiveTyping();
            
            // Set processing state
            setProcessingState(true);
            
            console.log("Generating speech for:", text);
            
            // Generate speech first
            const response = await fetch('/api/speak', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                console.error("Failed to generate speech:", data.error || "Unknown error");
                element.textContent = text;
                setProcessingState(false);
                return;
            }
            
            // Create and set up audio element
            audioElement = new Audio(data.audio_url);
            
            // Add these lines to prevent caching
            audioElement.setAttribute('crossorigin', 'anonymous');
            audioElement.oncanplaythrough = () => {
                console.log("Audio loaded successfully, length:", audioElement.duration);
            };
            audioElement.onerror = (error) => {
                console.error("Audio loading error:", error);
                element.textContent = text;
                setProcessingState(false);
            };
            
            // To force downloading fresh audio each time
            if (audioElement.src && audioElement.src === data.audio_url) {
                // Force reload if URL is the same (shouldn't happen with our cache busting)
                audioElement.load();
            }
            
            // Calculate typing speed based on audio duration
            audioElement.addEventListener('loadedmetadata', () => {
                const audioDuration = audioElement.duration * 1000; // convert to ms
                const typingSpeed = Math.max(10, Math.floor(audioDuration / text.length));
                
                // Start playing audio
                audioElement.play().catch(error => {
                    console.error('Failed to play audio:', error);
                    setProcessingState(false);
                });
                
                // Clear the response element
                element.textContent = '';
                buddyDot.classList.add('speaking');
                isTypingActive = true;
                
                // Simpler approach - type directly into the element without manual line breaking
                let displayedText = '';
                let currentIndex = 0;
                
                activeTypingInterval = setInterval(() => {
                    if (currentIndex < text.length) {
                        const nextChar = text.charAt(currentIndex);
                        displayedText += nextChar;
                        element.textContent = displayedText;
                        currentIndex++;
                    } else {
                        cancelActiveTyping();
                        setProcessingState(false);
                    }
                }, typingSpeed);
                
                // Clean up when audio ends
                audioElement.addEventListener('ended', () => {
                    cancelActiveTyping();
                    // Make sure all text is displayed when audio ends
                    element.textContent = text;
                    setProcessingState(false);
                });
                
                audioElement.addEventListener('error', (e) => {
                    console.error('Audio playback error:', e);
                    cancelActiveTyping();
                    element.textContent = text;
                    setProcessingState(false);
                });
            });
            
            audioElement.addEventListener('error', (e) => {
                console.error('Audio loading error:', e);
                element.textContent = text;
                setProcessingState(false);
            });
            
        } catch (error) {
            console.error('Error in speech and typing:', error);
            element.textContent = text;
            cancelActiveTyping();
            setProcessingState(false);
        }
    }
    
    // Function to cancel any active typing animation
    function cancelActiveTyping() {
        if (activeTypingInterval) {
            clearInterval(activeTypingInterval);
            activeTypingInterval = null;
        }
        
        // Stop any playing audio
        if (audioElement && !audioElement.paused) {
            audioElement.pause();
            audioElement.currentTime = 0;
        }
        
        isTypingActive = false;
        buddyDot.classList.remove('speaking');
    }
    
    // Set processing state to enable/disable UI controls
    function setProcessingState(processing) {
        isProcessing = processing;
        startListeningBtn.disabled = processing;
        sendTextBtn.disabled = processing;
        textInput.disabled = processing;
        
        if (processing) {
            startListeningBtn.classList.add('disabled');
            sendTextBtn.classList.add('disabled');
        } else {
            startListeningBtn.classList.remove('disabled');
            sendTextBtn.classList.remove('disabled');
            buddyDot.classList.remove('speaking');
            buddyDot.classList.remove('listening');
        }
    }
    
    // Function to load article details
    async function loadArticleDetails(articleId, shouldSpeak = true) {
        try {
            // Prevent multiple concurrent loadings
            if (isProcessing) return;
            
            // Cancel any active typing before proceeding
            cancelActiveTyping();
            
            setProcessingState(true);
            
            // Set current article ID
            currentArticleId = articleId;
            
            // Show loading message
            responseText.textContent = `Loading article ${articleId}...`;
            
            const response = await fetch('/api/news/details', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ article_id: articleId }),
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Hide news headlines
                newsHeadlines.style.display = 'none';
                
                // Reset article details scroll position
                articleDetails.scrollTop = 0;
                
                // Update article details
                articleTitle.textContent = data.title;
                
                // Make sure Back to Headlines button is visible
                const backButton = document.getElementById('back-to-headlines');
                backButton.style.display = 'block';
                
                // Format the metadata
                const formattedDate = data.date ? new Date(data.date).toLocaleDateString() : 'Unknown date';
                articleMeta.innerHTML = `
                    <span>Source: ${data.source || 'Unknown'}</span>
                    <span>Published: ${formattedDate}</span>
                `;
                
                // Add article image if available
                if (data.image_url) {
                    // Check if image container already exists
                    let articleImageContainer = document.getElementById('article-image-container');
                    if (!articleImageContainer) {
                        // Create new image container
                        articleImageContainer = document.createElement('div');
                        articleImageContainer.id = 'article-image-container';
                        articleImageContainer.classList.add('article-image-container');
                        
                        // Insert it before the content
                        articleContent.parentNode.insertBefore(articleImageContainer, articleContent);
                    }
                    
                    // Clear existing content
                    articleImageContainer.innerHTML = '';
                    
                    // Create the image element
                    const articleImage = document.createElement('img');
                    articleImage.id = 'article-image';
                    articleImage.classList.add('article-image');
                    articleImage.src = data.image_url;
                    articleImage.alt = data.title;
                    articleImage.onerror = function() {
                        // If image fails to load, hide the container
                        articleImageContainer.style.display = 'none';
                    };
                    
                    articleImageContainer.appendChild(articleImage);
                    articleImageContainer.style.display = 'block';
                }
                
                // Format content with newspaper style
                const contentText = data.content || 'No content available';
                articleContent.innerHTML = formatNewspaperText(contentText);
                
                // Clear previous analysis
                articleAnalysis.textContent = '';
                
                // Show article details
                articleDetails.style.display = 'block';
                
                // Reinforce back to headlines button functionality
                document.getElementById('back-to-headlines').onclick = function() {
                    // Cancel any active typing
                    cancelActiveTyping();
                    
                    articleDetails.style.display = 'none';
                    restoreNewsHeadlinesLayout();
                };
                
                // Add a close button to article details if it doesn't exist
                if (!articleDetails.querySelector('.article-close-btn')) {
                    const closeBtn = document.createElement('button');
                    closeBtn.className = 'article-close-btn';
                    closeBtn.innerHTML = '&times;';
                    closeBtn.style.position = 'absolute';
                    closeBtn.style.top = '10px';
                    closeBtn.style.right = '10px';
                    closeBtn.style.zIndex = '105'; // Higher than article details
                    closeBtn.style.background = '#000';
                    closeBtn.style.color = '#fff';
                    closeBtn.style.border = 'none';
                    closeBtn.style.borderRadius = '50%';
                    closeBtn.style.width = '30px';
                    closeBtn.style.height = '30px';
                    closeBtn.style.display = 'flex';
                    closeBtn.style.justifyContent = 'center';
                    closeBtn.style.alignItems = 'center';
                    closeBtn.style.cursor = 'pointer';
                    closeBtn.style.fontSize = '18px';
                    closeBtn.addEventListener('click', () => {
                        // Cancel any active typing before closing
                        cancelActiveTyping();
                        articleDetails.style.display = 'none';
                        restoreNewsHeadlinesLayout();
                    });
                    articleDetails.appendChild(closeBtn);
                }
                
                // Update response text with a confirmation and summary
                const articleObj = currentNewsData.articles.find(a => a.id === parseInt(articleId));
                if (articleObj) {
                    const responseMessage = `Here's article ${articleId}: "${data.title}" from ${data.source || 'Unknown'}. You can ask me questions about this article directly in the main chat input below.`;
                    
                    // Decide whether to speak based on the parameter
                    if (shouldSpeak) {
                        speakAndTypeText(responseMessage, responseText);
                    } else {
                        // Just set the text without speaking
                        responseText.textContent = responseMessage;
                    }
                }
            } else {
                showErrorMessage('Sorry, I could not load the article details.');
            }
            
            setProcessingState(false);
        } catch (error) {
            console.error('Error loading article details:', error);
            showErrorMessage('Error loading article details. Please try again.');
            setProcessingState(false);
        }
    }
    
    // Helper function to format text in newspaper style
    function formatNewspaperText(text) {
        if (!text) return '<p>No content available</p>';
        
        // Split by paragraphs and format
        const paragraphs = text.split(/\n\n|\r\n\r\n|\n|\r\n/);
        return paragraphs
            .filter(p => p.trim() !== '')
            .map(p => `<p>${p.trim()}</p>`)
            .join('');
    }
    
    // Function to show error messages
    function showErrorMessage(message) {
        console.error("ERROR:", message);
        
        // Update response text to show the error
        const responseText = document.getElementById('response-text');
        if (responseText) {
            responseText.innerHTML = `<div class="error-message">${message}</div>`;
        }
        
        // If there's a toast/notification system, use it
        if (typeof createToast === 'function') {
            createToast('Error', message, 'error');
        }
        
        // Always reset processing state
        setProcessingState(false);
    }

    // Function to ask question about article
    async function askQuestionAboutArticle() {
        // This function is no longer needed - questions are now asked via the main input
        console.log("This function is deprecated - article questions now use the main input");
    }

    // Client-side recording setup
    async function setupRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };
            
            mediaRecorder.onstop = async () => {
                // Create audio blob and send to server
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                await sendAudioToServer(audioBlob);
                audioChunks = []; // Reset for next recording
            };
            
            return true;
        } catch (error) {
            console.error('Error accessing microphone:', error);
            responseText.textContent = 'Error: Please allow microphone access to use this feature.';
            setProcessingState(false);
            return false;
        }
    }
    
    // Send recorded audio to server
    async function sendAudioToServer(audioBlob) {
        try {
            // Create form data to send the audio file
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            
            setProcessingState(true);
            buddyDot.classList.add('speaking');
            responseText.textContent = 'Processing your audio...';
            
            const response = await fetch('/api/listen-upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Show what was heard
                if (data.user_input && data.user_input !== "Error" && data.user_input !== "Empty transcription") {
                    textInput.value = data.user_input;
                    responseText.textContent = `I heard: "${data.user_input}"`;
                    
                    // Check if the voice input is a navigation command
                    if (handleNavigationCommand(data.user_input)) {
                        // Display user message
                        displayUserMessage(data.user_input);
                        setProcessingState(false);
                        return;
                    }
                    
                    // Brief pause before showing response
                    setTimeout(() => {
                        // Speak and type the response
                        speakAndTypeText(data.response, responseText);
                    }, 1000);
                } else {
                    // Handle case where transcription failed
                    responseText.textContent = 'Sorry, I could not understand what you said. Please try again or type your message.';
                    setProcessingState(false);
                }
            } else {
                responseText.textContent = 'Sorry, I could not process your audio. Please try again.';
                setProcessingState(false);
            }
            
        } catch (error) {
            console.error('Error sending audio:', error);
            responseText.textContent = 'Error sending audio to the server. Please try again.';
            setProcessingState(false);
        }
    }

    // Function to start voice listening
    async function startListening() {
        // Prevent multiple clicks
        if (isProcessing) {
            return;
        }
        
        try {
            setProcessingState(true);
            
            // Setup recording if not already done
            if (!mediaRecorder) {
                const success = await setupRecording();
                if (!success) {
                    return;
                }
            }
            
            startListeningBtn.textContent = 'Listening...';
            buddyDot.classList.add('listening');
            responseText.textContent = 'Listening... Please speak now.';
            
            // Start recording
            audioChunks = [];
            mediaRecorder.start();
            
            // Automatically stop recording after 10 seconds (as a safety measure)
            setTimeout(() => {
                if (mediaRecorder && mediaRecorder.state === 'recording') {
                    mediaRecorder.stop();
                }
            }, 10000);
            
            // Add a stop button functionality
            setTimeout(() => {
                if (!isProcessing) return; // In case it was reset already
                
                startListeningBtn.textContent = 'Stop Listening';
                startListeningBtn.disabled = false;
                startListeningBtn.onclick = () => {
                    if (mediaRecorder && mediaRecorder.state === 'recording') {
                        mediaRecorder.stop();
                    }
                    resetListeningButton();
                };
            }, 1000);
            
        } catch (error) {
            console.error('Error:', error);
            responseText.textContent = 'Sorry, there was an error with the speech recognition. Please try again.';
            resetListeningButton();
        }
    }
    
    // Reset the listening button state
    function resetListeningButton() {
        startListeningBtn.textContent = 'Start Listening';
        startListeningBtn.onclick = startListening;
        buddyDot.classList.remove('listening');
        setProcessingState(false);
    }

    // Function to reset display area to initial state
    function resetDisplayArea() {
        // Get all content sections
        const displayArea = document.getElementById('display-area');
        const placeholderText = document.getElementById('display-placeholder');
        const newsContent = document.getElementById('news-content');
        const calendarContent = document.getElementById('calendar-content');
        const storyContent = document.getElementById('story-content');
        
        console.log("RESETTING DISPLAY AREA - hiding all content");
        
        // Hide all content sections
        if (newsContent) {
            newsContent.style.display = 'none';
            console.log("- Set newsContent to none");
        }
        
        if (calendarContent) {
            calendarContent.style.display = 'none';
            console.log("- Set calendarContent to none");
        }
        
        if (storyContent) {
            storyContent.style.display = 'none';
            storyContent.style.zIndex = '1'; // Ensure proper z-index
            console.log("- Set storyContent to none with z-index 1");
        }
        
        // Show placeholder text
        if (placeholderText) {
            placeholderText.style.display = 'block';
            console.log("- Set placeholderText to block");
        }
        
        // Make sure display area is visible
        if (displayArea) {
            displayArea.style.display = 'block';
            console.log("- Set displayArea to block");
        }
    }

    // Event Listeners
    sendTextBtn.addEventListener('click', () => {
        const message = textInput.value.trim();
        if (message) {
            sendTextMessage(message);
        }
    });
    
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const message = textInput.value.trim();
            if (message) {
                sendTextMessage(message);
            }
        }
    });
    
    // Start listening to audio when the button is clicked
    startListeningBtn.addEventListener('click', startListening);
    
    // Initialize back to headlines button functionality
    if (backToHeadlinesBtn) {
        backToHeadlinesBtn.addEventListener('click', () => {
            // Cancel any active typing before closing
            cancelActiveTyping();
            articleDetails.style.display = 'none';
            restoreNewsHeadlinesLayout();
        });
    }
    
    // Setup client-side recording
    setupRecording();

    // Mental state button click event
    if (document.getElementById('mental-state-button')) {
        document.getElementById('mental-state-button').addEventListener('click', () => {
            window.location.href = '/mental-state';
        });
    }

    // Close reminders when clicking outside the container
    document.addEventListener('click', function(e) {
        if (!remindersContainer) return;
        
        // Only process if reminders are visible
        if (remindersContainer.style.display === 'block') {
            // Check if click is outside reminders container and not on the reminders button
            if (!remindersContainer.contains(e.target) && 
                e.target !== reminderButton && 
                !reminderButton.contains(e.target)) {
                
                console.log("Click outside reminders detected - hiding container");
                remindersContainer.style.display = 'none';
            }
        }
    });
});

// Function to show calendar when button is clicked
async function showCalendar() {
    try {
        // Reset the display area
        resetDisplayArea();
        
        // Explicitly hide story content if it exists and set proper z-index
        const storyContent = document.getElementById('story-content');
        if (storyContent) {
            storyContent.style.display = 'none';
            storyContent.style.zIndex = '1'; // Ensure it's below calendar
            console.log("Explicitly hiding story content for calendar view");
        }
        
        // Show loading state in response text
        const responseText = document.getElementById('response-text');
        responseText.textContent = 'Loading your calendar...';
        
        // Fetch calendar data from the server
        const response = await fetch('/api/calendar/month');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const calendarData = await response.json();
        
        // Fetch upcoming events
        const eventsResponse = await fetch('/api/calendar/events/upcoming');
        if (!eventsResponse.ok) {
            throw new Error(`HTTP error! status: ${eventsResponse.status}`);
        }
        
        const eventsData = await eventsResponse.json();
        
        // Show calendar container
        const calendarContent = document.getElementById('calendar-content');
        calendarContent.style.display = 'flex';
        calendarContent.style.zIndex = '10'; // Ensure it's on top
        
        // Hide placeholder
        const displayArea = document.getElementById('display-area');
        const placeholderElements = displayArea.getElementsByClassName('placeholder-text');
        if (placeholderElements.length > 0) {
            placeholderElements[0].style.display = 'none';
        }
        
        // Display calendar
        displayCalendar(calendarData.calendar);
        
        // Update upcoming events
        updateUpcomingEvents(eventsData.events);
        
        // Update response text
        responseText.textContent = 'Here is your calendar. You can navigate between months and view your events.';
        
    } catch (error) {
        console.error('Error fetching calendar:', error);
        document.getElementById('response-text').textContent = 'Sorry, I encountered an error loading your calendar.';
    }
}

// Function to show only the story content area without affecting the response text
function showStoryContentOnly() {
    console.log("SHOWING STORY CONTENT ONLY");
    
    // Get display elements
    const displayArea = document.getElementById('display-area');
    const placeholder = document.getElementById('display-placeholder');
    const newsContent = document.getElementById('news-content');
    const calendarContent = document.getElementById('calendar-content');
    const storyContent = document.getElementById('story-content');
    
    // Log state before changes
    console.log("Before changes:");
    if (displayArea) console.log("- displayArea display:", displayArea.style.display);
    if (placeholder) console.log("- placeholder display:", placeholder.style.display);
    if (newsContent) console.log("- newsContent display:", newsContent.style.display);
    if (calendarContent) console.log("- calendarContent display:", calendarContent.style.display);
    if (storyContent) console.log("- storyContent display:", storyContent.style.display);
    
    // Make sure display area is visible
    if (displayArea) {
        displayArea.style.display = 'block';
        console.log("Set displayArea to block");
    }
    
    // Hide placeholder
    if (placeholder) {
        placeholder.style.display = 'none';
        console.log("Set placeholder to none");
    }
    
    // Hide news content
    if (newsContent) {
        newsContent.style.display = 'none';
        console.log("Set newsContent to none");
    }
    
    // Hide calendar content
    if (calendarContent) {
        calendarContent.style.display = 'none';
        console.log("Set calendarContent to none");
    }
    
    // Show story content
    if (storyContent) {
        storyContent.style.display = 'block';
        console.log("Set storyContent to block");
    } else {
        console.error("Story content element not found!");
        // Create it if missing
        createStoryContainers();
        
        // Try to get it again
        const newStoryContent = document.getElementById('story-content');
        if (newStoryContent) {
            newStoryContent.style.display = 'block';
            console.log("Created and set storyContent to block");
        }
    }
    
    // Log state after changes
    console.log("After changes:");
    if (displayArea) console.log("- displayArea display:", displayArea.style.display);
    if (placeholder) console.log("- placeholder display:", placeholder.style.display);
    if (newsContent) console.log("- newsContent display:", newsContent.style.display);
    if (calendarContent) console.log("- calendarContent display:", calendarContent.style.display);
    if (storyContent) console.log("- storyContent display:", storyContent.style.display);
}

// Functions to handle story-related content
function handleStoryResponse(data) {
    console.log("DEPRECATED - This function should NOT be called - using showStoryImages directly instead");
    console.log("If you see this message, there's a conflict in the code - both handleStoryResponse and showStoryImages are being called");
    
    // Just forward to our new implementation
    if (data.story_data && data.story_data.media_ids) {
        showStoryImages(data.story_data.media_ids);
    }
}

// Lightbox for story images
function openLightbox(imageSrc) {
    // Create lightbox elements if they don't exist
    if (!document.getElementById('lightbox-overlay')) {
        const lightboxOverlay = document.createElement('div');
        lightboxOverlay.id = 'lightbox-overlay';
        lightboxOverlay.className = 'lightbox-overlay';
        
        const lightboxContent = document.createElement('div');
        lightboxContent.id = 'lightbox-content';
        lightboxContent.className = 'lightbox-content';
        
        const lightboxImage = document.createElement('img');
        lightboxImage.id = 'lightbox-image';
        lightboxImage.className = 'lightbox-image';
        
        const closeButton = document.createElement('button');
        closeButton.id = 'lightbox-close';
        closeButton.className = 'lightbox-close';
        closeButton.innerHTML = '&times;';
        
        lightboxContent.appendChild(lightboxImage);
        lightboxContent.appendChild(closeButton);
        lightboxOverlay.appendChild(lightboxContent);
        document.body.appendChild(lightboxOverlay);
        
        // Add event listeners
        closeButton.addEventListener('click', closeLightbox);
        lightboxOverlay.addEventListener('click', (e) => {
            if (e.target === lightboxOverlay) {
                closeLightbox();
            }
        });
    }
    
    // Set image source and show lightbox
    const lightboxImage = document.getElementById('lightbox-image');
    lightboxImage.src = imageSrc;
    
    const lightboxOverlay = document.getElementById('lightbox-overlay');
    lightboxOverlay.style.display = 'flex';
    
    // Prevent scrolling on the body
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    const lightboxOverlay = document.getElementById('lightbox-overlay');
    if (lightboxOverlay) {
        lightboxOverlay.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// Reset display without changing the response text
function resetDisplayWithoutResponse() {
    // Hide all content sections
    if (newsContent) newsContent.style.display = 'none';
    if (calendarContent) calendarContent.style.display = 'none';
    if (storyContent) storyContent.style.display = 'none';
    
    // Show placeholder
    if (placeholderText) placeholderText.style.display = 'block';
}

// Function to display just the story images without affecting the response text
function showStoryImages(mediaIds) {
    console.log("%c === STEP 5 - STORY IMAGE PROCESSING STARTED === ", "background: #4CAF50; color: white; font-weight: bold;");
    console.log("Function called with mediaIds:", JSON.stringify(mediaIds));
    
    // CRITICAL CHECK: Ensure we have valid media IDs
    if (!mediaIds || !Array.isArray(mediaIds) || mediaIds.length === 0) {
        console.error("No valid media IDs provided:", mediaIds);
        return;
    }
    
    // First thing: Create a debug display in the UI
    const debugEl = document.createElement('div');
    debugEl.style.position = 'fixed';
    debugEl.style.top = '10px';
    debugEl.style.right = '10px';
    debugEl.style.backgroundColor = 'rgba(0,0,0,0.8)';
    debugEl.style.color = 'white';
    debugEl.style.padding = '10px';
    debugEl.style.borderRadius = '5px';
    debugEl.style.zIndex = '9999';
    debugEl.style.maxWidth = '400px';
    debugEl.style.maxHeight = '300px';
    debugEl.style.overflow = 'auto';
    debugEl.innerHTML = `
        <h3>Story Image Debug</h3>
        <p>MediaIDs: ${JSON.stringify(mediaIds)}</p>
        <div id="image-load-status"></div>
        <button onclick="this.parentNode.style.display='none'">Close</button>
    `;
    document.body.appendChild(debugEl);
    
    // Function to update the debug display
    function updateDebug(message) {
        const status = document.getElementById('image-load-status');
        if (status) {
            status.innerHTML += `<div>${message}</div>`;
        }
        console.log(message);
    }
    
    updateDebug('Starting image load process...');
    
    // STEP 1: Make sure all required container elements exist
    updateDebug('STEP 1: Checking container elements...');
    
    // Get the display area - create it if it doesn't exist
    let displayArea = document.getElementById('display-area');
    if (!displayArea) {
        updateDebug('ERROR: display-area not found, creating it');
        displayArea = document.createElement('div');
        displayArea.id = 'display-area';
        displayArea.className = 'display-area';
        document.querySelector('.right-panel').appendChild(displayArea);
    }
    
    // Hide the placeholder if it exists
    const placeholder = document.getElementById('display-placeholder');
    if (placeholder) {
        placeholder.style.display = 'none';
        updateDebug('Hidden placeholder');
    }
    
    // Get or create the story content container
    let storyContent = document.getElementById('story-content');
    if (!storyContent) {
        updateDebug('Creating story-content element');
        storyContent = document.createElement('div');
        storyContent.id = 'story-content';
        storyContent.className = 'content-section';
        displayArea.appendChild(storyContent);
    }
    
    // Get or create the story images container
    let storyImagesContainer = document.getElementById('story-images-container');
    if (!storyImagesContainer) {
        updateDebug('Creating story-images-container element');
        storyImagesContainer = document.createElement('div');
        storyImagesContainer.id = 'story-images-container';
        storyImagesContainer.className = 'story-images-container';
        storyContent.appendChild(storyImagesContainer);
    }
    
    // STEP 2: Make sure display area is visible
    updateDebug('STEP 2: Setting visibility...');
    displayArea.style.display = 'block';
    storyContent.style.display = 'block';
    
    // Hide any other content
    const newsContent = document.getElementById('news-content');
    if (newsContent) {
        newsContent.style.display = 'none';
        updateDebug('Hidden news-content');
    }
    
    const calendarContent = document.getElementById('calendar-content');
    if (calendarContent) {
        calendarContent.style.display = 'none';
        updateDebug('Hidden calendar-content');
    }
    
    // STEP 3: Clear existing images and prepare container
    updateDebug('STEP 3: Clearing existing content...');
    storyImagesContainer.innerHTML = '';
    
    // Add a heading to indicate these are related images
    const heading = document.createElement('div');
    heading.className = 'story-images-heading';
    heading.textContent = 'Related Images';
    storyImagesContainer.appendChild(heading);
    
    // STEP 4: Add each image to the container
    updateDebug(`STEP 4: Processing ${mediaIds.length} images...`);
    
    mediaIds.forEach((mediaId, index) => {
        updateDebug(`Processing image ${index + 1}/${mediaIds.length}: ${mediaId}`);
        
        // Create image container
        const imageContainer = document.createElement('div');
        imageContainer.className = 'story-image-container';
        imageContainer.style.width = '250px';
        imageContainer.style.height = '250px';
        imageContainer.style.border = '1px solid #ddd';
        imageContainer.style.borderRadius = '8px';
        imageContainer.style.overflow = 'hidden';
        imageContainer.style.position = 'relative';
        imageContainer.style.display = 'flex';
        imageContainer.style.alignItems = 'center';
        imageContainer.style.justifyContent = 'center';
        imageContainer.style.backgroundColor = '#f8f8f8';
        
        // Create image element
        const image = document.createElement('img');
        image.className = 'story-image';
        image.style.maxWidth = '100%';
        image.style.maxHeight = '100%';
        image.style.objectFit = 'contain';
        image.style.transition = 'transform 0.3s ease';
        const imageSrc = `/story_images/${mediaId}`;
        image.src = imageSrc;
        image.alt = `Story Image: ${mediaId}`;
        
        // Add hover effects
        imageContainer.onmouseover = function() {
            image.style.transform = 'scale(1.05)';
        };
        imageContainer.onmouseout = function() {
            image.style.transform = 'scale(1)';
        };
        
        // Add loading indicator
        const loader = document.createElement('div');
        loader.className = 'image-loading';
        loader.style.position = 'absolute';
        loader.style.top = '0';
        loader.style.left = '0';
        loader.style.width = '100%';
        loader.style.height = '100%';
        loader.style.display = 'flex';
        loader.style.alignItems = 'center';
        loader.style.justifyContent = 'center';
        loader.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';
        loader.style.zIndex = '5';
        
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        spinner.style.width = '40px';
        spinner.style.height = '40px';
        spinner.style.border = '4px solid #f3f3f3';
        spinner.style.borderTop = '4px solid #3498db';
        spinner.style.borderRadius = '50%';
        spinner.style.animation = 'spin 1.5s linear infinite';
        
        // Add keyframes for spinner animation
        if (!document.getElementById('spinner-keyframes')) {
            const style = document.createElement('style');
            style.id = 'spinner-keyframes';
            style.textContent = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }
        
        loader.appendChild(spinner);
        imageContainer.appendChild(loader);
        
        // Handle image loading events with better visibility
        image.onload = function() {
            updateDebug(`✅ Image loaded: ${mediaId} (${this.naturalWidth}x${this.naturalHeight})`);
            loader.style.display = 'none';
            
            // Add visual indication of successful load
            const successIndicator = document.createElement('div');
            successIndicator.style.position = 'absolute';
            successIndicator.style.top = '10px';
            successIndicator.style.right = '10px';
            successIndicator.style.backgroundColor = '#4CAF50';
            successIndicator.style.color = 'white';
            successIndicator.style.width = '24px';
            successIndicator.style.height = '24px';
            successIndicator.style.borderRadius = '50%';
            successIndicator.style.display = 'flex';
            successIndicator.style.alignItems = 'center';
            successIndicator.style.justifyContent = 'center';
            successIndicator.style.fontSize = '14px';
            successIndicator.style.fontWeight = 'bold';
            successIndicator.innerHTML = '✓';
            successIndicator.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
            imageContainer.appendChild(successIndicator);
            
            imageContainer.classList.add('image-loaded-success');
        };
        
        image.onerror = function(error) {
            updateDebug(`❌ Failed to load: ${mediaId}`);
            loader.style.display = 'none';
            imageContainer.classList.add('image-fallback');
            this.style.display = 'none';
            
            // Create a more visually appealing fallback
            const fallbackContainer = document.createElement('div');
            fallbackContainer.style.width = '100%';
            fallbackContainer.style.height = '100%';
            fallbackContainer.style.display = 'flex';
            fallbackContainer.style.flexDirection = 'column';
            fallbackContainer.style.alignItems = 'center';
            fallbackContainer.style.justifyContent = 'center';
            fallbackContainer.style.padding = '20px';
            fallbackContainer.style.boxSizing = 'border-box';
            fallbackContainer.style.textAlign = 'center';
            
            // Add error icon
            const errorIcon = document.createElement('div');
            errorIcon.style.fontSize = '32px';
            errorIcon.style.color = '#d9534f';
            errorIcon.innerHTML = '❌';
            errorIcon.style.marginBottom = '10px';
            fallbackContainer.appendChild(errorIcon);
            
            // Filename with truncation if too long
            const filename = mediaId.length > 20 ? mediaId.substring(0, 17) + '...' : mediaId;
            const fallbackText = document.createElement('div');
            fallbackText.className = 'image-fallback-text';
            fallbackText.style.fontWeight = 'bold';
            fallbackText.style.marginBottom = '10px';
            fallbackText.textContent = filename;
            fallbackContainer.appendChild(fallbackText);
            
            // Error message
            const errorMessage = document.createElement('div');
            errorMessage.style.fontSize = '12px';
            errorMessage.style.color = '#777';
            errorMessage.textContent = 'Image failed to load';
            fallbackContainer.appendChild(errorMessage);
            
            // Retry button
            const retryButton = document.createElement('button');
            retryButton.textContent = 'Retry Loading';
            retryButton.style.marginTop = '10px';
            retryButton.style.padding = '5px 10px';
            retryButton.style.backgroundColor = '#5bc0de';
            retryButton.style.color = 'white';
            retryButton.style.border = 'none';
            retryButton.style.borderRadius = '4px';
            retryButton.style.cursor = 'pointer';
            retryButton.onclick = function() {
                // Try to load the image again with cache busting
                imageContainer.innerHTML = '';
                const newImage = new Image();
                newImage.className = 'story-image';
                newImage.style.maxWidth = '100%';
                newImage.style.maxHeight = '100%';
                newImage.style.objectFit = 'contain';
                newImage.src = imageSrc + '?t=' + new Date().getTime();
                newImage.alt = `Story Image: ${mediaId}`;
                imageContainer.appendChild(newImage);
                
                // Add new loader
                const newLoader = document.createElement('div');
                newLoader.style.position = 'absolute';
                newLoader.style.inset = '0';
                newLoader.style.backgroundColor = 'rgba(255,255,255,0.8)';
                newLoader.style.display = 'flex';
                newLoader.style.alignItems = 'center';
                newLoader.style.justifyContent = 'center';
                newLoader.innerHTML = '<div style="width:30px;height:30px;border:3px solid #f3f3f3;border-top:3px solid #3498db;border-radius:50%;animation:spin 1s linear infinite"></div>';
                imageContainer.appendChild(newLoader);
                
                newImage.onload = function() {
                    newLoader.remove();
                    imageContainer.classList.remove('image-fallback');
                    imageContainer.classList.add('image-loaded-success');
                };
                
                newImage.onerror = function() {
                    imageContainer.innerHTML = '';
                    imageContainer.appendChild(fallbackContainer);
                };
            };
            fallbackContainer.appendChild(retryButton);
            
            imageContainer.appendChild(fallbackContainer);
            
            // Try direct fetch to check status
            fetch(imageSrc)
                .then(response => {
                    updateDebug(`Fetch status: ${response.status} ${response.statusText}`);
                    errorMessage.textContent = `Status: ${response.status} ${response.statusText}`;
                })
                .catch(err => {
                    updateDebug(`Fetch error: ${err.message}`);
                    errorMessage.textContent = `Error: ${err.message}`;
                });
        };
        
        // Add lightbox functionality 
        image.addEventListener('click', () => {
            openLightbox(image.src);
        });
        
        // Add to DOM
        imageContainer.appendChild(image);
        storyImagesContainer.appendChild(imageContainer);
    });
    
    // Final check to ensure everything is visible
    updateDebug('STEP 5: Final visibility check...');
    displayArea.style.display = 'block';
    storyContent.style.display = 'block';
    
    // CRITICAL FIX: Ensure the story content area is visible and properly positioned
    storyContent.style.zIndex = '100';
    storyContent.style.position = 'relative';
    storyContent.style.backgroundColor = '#fff';
    storyContent.style.width = '100%';
    storyContent.style.height = 'auto';
    storyContent.style.minHeight = '200px';
    storyContent.style.padding = '20px';
    storyContent.style.boxShadow = '0 0 10px rgba(0,0,0,0.1)';
    storyContent.style.borderRadius = '8px';
    storyContent.style.margin = '15px 0';
    
    // Make sure the images container is visible
    storyImagesContainer.style.display = 'flex';
    storyImagesContainer.style.flexWrap = 'wrap';
    storyImagesContainer.style.justifyContent = 'center';
    storyImagesContainer.style.gap = '15px';
    storyImagesContainer.style.width = '100%';
    
    // Force reflow to ensure display updates
    void displayArea.offsetHeight;
    
    updateDebug('Image processing complete!');
}

// Function to create story containers if they don't exist
function createStoryContainers() {
    console.log("Creating story containers...");
    
    // Get display area
    const displayArea = document.getElementById('display-area');
    if (!displayArea) {
        console.error("ERROR: Display area not found!");
        return;
    }
    
    // Create story content if it doesn't exist
    if (!document.getElementById('story-content')) {
        // Create story content container
        const storyContent = document.createElement('div');
        storyContent.id = 'story-content';
        storyContent.className = 'content-section';
        storyContent.style.display = 'none';
        
        // Create story images container
        const storyImagesContainer = document.createElement('div');
        storyImagesContainer.id = 'story-images-container';
        storyImagesContainer.className = 'story-images-container';
        
        // Create back button similar to the news one
        const backBtn = document.createElement('button');
        backBtn.id = 'back-from-story';
        backBtn.className = 'back-button';
        backBtn.textContent = '← Back';
        
        // Add elements to DOM
        storyContent.appendChild(backBtn);
        storyContent.appendChild(storyImagesContainer);
        displayArea.appendChild(storyContent);
        
        // Add event listener to back button
        backBtn.addEventListener('click', () => {
            resetDisplayArea();
        });
        
        console.log("Created new story containers");
    }
}

// Debug function to inspect and dump the complete object structure
function debugObjectStructure(obj, name = "object", maxDepth = 3) {
    console.log(`=== DEBUG: ${name} STRUCTURE DUMP ===`);
    
    function stringify(obj, depth = 0) {
        if (depth > maxDepth) return "...";
        
        if (obj === null) return "null";
        if (obj === undefined) return "undefined";
        
        const type = typeof obj;
        
        if (type !== "object") {
            if (type === "string") return `"${obj}"`;
            return String(obj);
        }
        
        if (Array.isArray(obj)) {
            if (obj.length === 0) return "[]";
            let result = "[\n";
            obj.forEach((item, i) => {
                result += "  ".repeat(depth + 1) + `${i}: ${stringify(item, depth + 1)}`;
                if (i < obj.length - 1) result += ",";
                result += "\n";
            });
            result += "  ".repeat(depth) + "]";
            return result;
        }
        
        const keys = Object.keys(obj);
        if (keys.length === 0) return "{}";
        
        let result = "{\n";
        keys.forEach((key, i) => {
            result += "  ".repeat(depth + 1) + `${key}: ${stringify(obj[key], depth + 1)}`;
            if (i < keys.length - 1) result += ",";
            result += "\n";
        });
        result += "  ".repeat(depth) + "}";
        return result;
    }
    
    console.log(stringify(obj));
    console.log(`=== END DEBUG: ${name} STRUCTURE DUMP ===`);
    
    return obj; // Return original object for chaining
}

// Function to check available story images on the server
function checkAvailableStoryImages() {
    console.log("%c === CHECKING AVAILABLE STORY IMAGES === ", "background: #9c27b0; color: white; font-weight: bold;");
    
    fetch('/api/debug/story-images')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("%c STORY IMAGES DEBUG INFO ", "background: #9c27b0; color: white; font-weight: bold;");
            console.log("Directory:", data.directory);
            console.log("Directory exists:", data.directory_exists);
            console.log("Image count:", data.image_count);
            console.log("Story JSON exists:", data.story_json_exists);
            console.log("Embeddings exist:", data.embeddings_exist);
            
            if (data.images && data.images.length > 0) {
                console.log("Available images:");
                data.images.forEach(img => {
                    console.log(`- ${img.filename} (${img.size_bytes} bytes, modified: ${img.last_modified})`);
                });
                
                // Create debug info in the DOM
                const debugInfo = document.createElement('div');
                debugInfo.className = 'story-debug-info';
                debugInfo.innerHTML = `
                    <h3>Available Images (${data.image_count})</h3>
                    <ul>
                        ${data.images.map(img => `
                            <li>
                                ${img.filename} (${Math.round(img.size_bytes/1024)}KB)
                                <button onclick="retrySpecificImage('${img.filename}')">Load This</button>
                            </li>
                        `).join('')}
                    </ul>
                `;
                
                // Add to the story images container
                const storyImagesContainer = document.getElementById('story-images-container');
                if (storyImagesContainer) {
                    storyImagesContainer.appendChild(debugInfo);
                }
            } else {
                console.log("No images available on server");
            }
        })
        .catch(error => {
            console.error("Error checking available story images:", error);
        });
}

// Function to retry loading a specific image
function retrySpecificImage(filename) {
    console.log(`Attempting to load image: ${filename}`);
    
    // Create a container for the image
    const storyImagesContainer = document.getElementById('story-images-container');
    if (!storyImagesContainer) return;
    
    // Create image container
    const imageContainer = document.createElement('div');
    imageContainer.className = 'story-image-container retry-container';
    
    // Create image element
    const image = document.createElement('img');
    image.className = 'story-image';
    const imageSrc = `/story_images/${filename}?t=${Date.now()}`; // Add cache buster
    image.src = imageSrc;
    image.alt = `Story Image: ${filename}`;
    
    // Add loading indicator
    const loader = document.createElement('div');
    loader.className = 'image-loading';
    loader.innerHTML = '<div class="spinner"></div>';
    imageContainer.appendChild(loader);
    
    // Handle image loading events
    image.onload = function() {
        console.log(`%c ✅ SUCCESS: Image "${filename}" loaded successfully`, "color: green; font-weight: bold");
        loader.style.display = 'none';
        
        // Verify the image has actual dimensions
        console.log(`Image dimensions: ${this.naturalWidth}x${this.naturalHeight}`);
        
        // Add success class for debugging
        imageContainer.classList.add('image-loaded-success');
    };
    
    image.onerror = function(error) {
        console.error(`Failed to load image: ${filename}`, error);
        loader.style.display = 'none';
        imageContainer.classList.add('image-fallback');
        this.style.display = 'none';
        
        const fallbackText = document.createElement('div');
        fallbackText.className = 'image-fallback-text';
        fallbackText.textContent = `${filename} - Failed to load`;
        imageContainer.appendChild(fallbackText);
    };
    
    // Add to container
    imageContainer.appendChild(image);
    storyImagesContainer.appendChild(imageContainer);
} 

// Add this at the end of the document ready function
$(document).ready(function() {
    // ... existing code ...
    
    // Add direct image test function
    window.testImageLoading = function() {
        console.log("Testing image loading...");
        
        // Create test container
        const testContainer = document.createElement('div');
        testContainer.style.position = 'fixed';
        testContainer.style.bottom = '10px';
        testContainer.style.right = '10px';
        testContainer.style.backgroundColor = 'white';
        testContainer.style.border = '2px solid #333';
        testContainer.style.padding = '10px';
        testContainer.style.zIndex = '9999';
        
        // Add heading
        const heading = document.createElement('h3');
        heading.textContent = 'Image Load Test';
        testContainer.appendChild(heading);
        
        // Add test image for memory_box.jpg
        const img1 = new Image();
        img1.src = '/story_images/memory_box.jpg?t=' + Date.now();
        img1.style.maxWidth = '150px';
        img1.style.border = '1px solid #ccc';
        img1.style.display = 'block';
        img1.style.marginBottom = '10px';
        
        const label1 = document.createElement('p');
        label1.textContent = 'Testing: memory_box.jpg';
        
        // Add test image for car_packed.jpg
        const img2 = new Image();
        img2.src = '/story_images/car_packed.jpg?t=' + Date.now();
        img2.style.maxWidth = '150px';
        img2.style.border = '1px solid #ccc';
        img2.style.display = 'block';
        img2.style.marginBottom = '10px';
        
        const label2 = document.createElement('p');
        label2.textContent = 'Testing: car_packed.jpg';
        
        // Add status div
        const status = document.createElement('div');
        status.id = 'test-status';
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Close';
        closeBtn.onclick = function() {
            testContainer.remove();
        };
        
        // Add elements to container
        testContainer.appendChild(label1);
        testContainer.appendChild(img1);
        testContainer.appendChild(label2);
        testContainer.appendChild(img2);
        testContainer.appendChild(status);
        testContainer.appendChild(closeBtn);
        
        // Add container to body
        document.body.appendChild(testContainer);
        
        // Handle load/error events
        img1.onload = function() {
            console.log("memory_box.jpg loaded successfully!");
            label1.innerHTML = '✅ memory_box.jpg loaded! (' + img1.naturalWidth + 'x' + img1.naturalHeight + ')';
        };
        
        img1.onerror = function() {
            console.error("Failed to load memory_box.jpg");
            label1.innerHTML = '❌ Failed to load memory_box.jpg';
            
            // Try fetch to get status
            fetch('/story_images/memory_box.jpg')
                .then(response => {
                    label1.innerHTML += ` (Status: ${response.status})`;
                })
                .catch(err => {
                    label1.innerHTML += ` (Error: ${err.message})`;
                });
        };
        
        img2.onload = function() {
            console.log("car_packed.jpg loaded successfully!");
            label2.innerHTML = '✅ car_packed.jpg loaded! (' + img2.naturalWidth + 'x' + img2.naturalHeight + ')';
        };
        
        img2.onerror = function() {
            console.error("Failed to load car_packed.jpg");
            label2.innerHTML = '❌ Failed to load car_packed.jpg';
            
            // Try fetch to get status
            fetch('/story_images/car_packed.jpg')
                .then(response => {
                    label2.innerHTML += ` (Status: ${response.status})`;
                })
                .catch(err => {
                    label2.innerHTML += ` (Error: ${err.message})`;
                });
        };
    };
    
    // Call the test function after a short delay
    setTimeout(testImageLoading, 1000);
    
    // Add test image loading button to the UI
    const testButton = document.createElement('button');
    testButton.textContent = 'Test Image Loading';
    testButton.style.position = 'fixed';
    testButton.style.bottom = '10px';
    testButton.style.left = '10px';
    testButton.style.zIndex = '1000';
    testButton.style.padding = '8px 12px';
    testButton.style.backgroundColor = '#4CAF50';
    testButton.style.color = 'white';
    testButton.style.border = 'none';
    testButton.style.borderRadius = '4px';
    testButton.style.cursor = 'pointer';
    testButton.onclick = testImageLoading;
    document.body.appendChild(testButton);
    
    // Call the test function after a short delay
    setTimeout(testImageLoading, 1000);
});

// Function to directly display story images using the same approach as the test script
function displayStoryImagesDirectly(mediaIds) {
    console.log("DIRECT STORY IMAGE DISPLAY:", mediaIds);
    
    // Get display area
    const displayArea = document.getElementById('display-area');
    if (!displayArea) {
        console.error("Display area not found!");
        return;
    }
    
    // Make sure display area is visible
    displayArea.style.display = 'block';
    
    // Hide placeholder if it exists
    const placeholder = document.getElementById('display-placeholder');
    if (placeholder) {
        placeholder.style.display = 'none';
    }
    
    // Create or get story content area
    let storyContent = document.getElementById('story-content');
    if (!storyContent) {
        storyContent = document.createElement('div');
        storyContent.id = 'story-content';
        storyContent.className = 'content-section';
        displayArea.appendChild(storyContent);
    }
    
    // Show and clear the story content
    storyContent.style.display = 'block';
    storyContent.innerHTML = '';
    
    // Create image container
    const imageContainer = document.createElement('div');
    imageContainer.className = 'story-images-container';
    imageContainer.style.display = 'flex';
    imageContainer.style.flexWrap = 'wrap';
    imageContainer.style.justifyContent = 'center';
    imageContainer.style.gap = '25px';
    imageContainer.style.padding = '25px';
    imageContainer.style.margin = '20px 0';
    imageContainer.style.borderRadius = '12px';
    imageContainer.style.backgroundColor = '#f7f9fc';
    imageContainer.style.boxShadow = '0 4px 12px rgba(0,0,0,0.05)';
    
    // Add heading
    const heading = document.createElement('h3');
    heading.textContent = 'Related Images';
    heading.style.width = '100%';
    heading.style.textAlign = 'center';
    heading.style.marginBottom = '20px';
    heading.style.color = '#2c3e50';
    heading.style.fontFamily = 'Arial, sans-serif';
    heading.style.fontSize = '18px';
    heading.style.fontWeight = '600';
    heading.style.borderBottom = '2px solid #e1e8ed';
    heading.style.paddingBottom = '12px';
    imageContainer.appendChild(heading);
    
    // Process each image
    mediaIds.forEach((mediaId, index) => {
        // Create individual image wrapper
        const imageWrapper = document.createElement('div');
        imageWrapper.style.width = '280px';
        imageWrapper.style.position = 'relative';
        imageWrapper.style.borderRadius = '10px';
        imageWrapper.style.overflow = 'hidden';
        imageWrapper.style.boxShadow = '0 5px 15px rgba(0,0,0,0.08)';
        imageWrapper.style.backgroundColor = 'white';
        imageWrapper.style.transition = 'transform 0.3s ease, box-shadow 0.3s ease';
        
        // Add hover effect
        imageWrapper.onmouseover = function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 8px 20px rgba(0,0,0,0.12)';
        };
        imageWrapper.onmouseout = function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 5px 15px rgba(0,0,0,0.08)';
        };
        
        // Create image container
        const imageBox = document.createElement('div');
        imageBox.style.width = '100%';
        imageBox.style.height = '220px';
        imageBox.style.display = 'flex';
        imageBox.style.alignItems = 'center';
        imageBox.style.justifyContent = 'center';
        imageBox.style.position = 'relative';
        imageBox.style.backgroundColor = '#f8f8f8';
        imageBox.style.overflow = 'hidden';
        
        // Loading spinner
        const spinner = document.createElement('div');
        spinner.style.border = '4px solid rgba(0,0,0,0.1)';
        spinner.style.borderTop = '4px solid #3498db';
        spinner.style.borderRadius = '50%';
        spinner.style.width = '40px';
        spinner.style.height = '40px';
        spinner.style.position = 'absolute';
        spinner.style.animation = 'spin 1s linear infinite';
        imageBox.appendChild(spinner);
        
        // Add keyframes for spinner if needed
        if (!document.getElementById('spinner-keyframes')) {
            const style = document.createElement('style');
            style.id = 'spinner-keyframes';
            style.textContent = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Create image element
        const image = new Image();
        image.src = `/story_images/${mediaId}`;
        image.alt = `Story Image: ${mediaId}`;
        image.style.maxWidth = '100%';
        image.style.maxHeight = '100%';
        image.style.objectFit = 'cover';
        image.style.borderRadius = '4px';
        image.style.transition = 'transform 0.5s ease';
        
        // Add image hover zoom effect
        imageBox.onmouseover = function() {
            image.style.transform = 'scale(1.1)';
        };
        imageBox.onmouseout = function() {
            image.style.transform = 'scale(1)';
        };
        
        // Handle image load event
        image.onload = function() {
            console.log(`Image loaded: ${mediaId}`);
            spinner.style.display = 'none';
            imageBox.style.backgroundColor = 'transparent';
        };
        
        // Handle image error event
        image.onerror = function() {
            console.error(`Failed to load image: ${mediaId}`);
            spinner.style.display = 'none';
            imageBox.style.backgroundColor = '#fff5f5';
            
            // Add error message
            const errorMsg = document.createElement('div');
            errorMsg.textContent = 'Image failed to load';
            errorMsg.style.color = '#e74c3c';
            errorMsg.style.fontSize = '14px';
            errorMsg.style.padding = '10px';
            errorMsg.style.textAlign = 'center';
            imageBox.appendChild(errorMsg);
        };
        
        // Add image to container
        imageBox.appendChild(image);
        imageWrapper.appendChild(imageBox);
        
        // Add caption
        const caption = document.createElement('div');
        caption.style.padding = '12px 15px';
        caption.style.backgroundColor = 'white';
        caption.style.color = '#34495e';
        caption.style.fontSize = '14px';
        caption.style.textAlign = 'center';
        caption.style.fontFamily = 'Arial, sans-serif';
        
        // Format the filename to look better
        const prettyName = mediaId
            .replace(/_/g, ' ')
            .replace(/\.\w+$/, '')
            .replace(/\b\w/g, l => l.toUpperCase());
        
        caption.textContent = prettyName;
        imageWrapper.appendChild(caption);
        
        // Lightbox functionality
        imageWrapper.addEventListener('click', function() {
            openLightbox(image.src);
        });
        
        // Add completed wrapper to container
        imageContainer.appendChild(imageWrapper);
    });
    
    // Add the image container to story content
    storyContent.appendChild(imageContainer);
}