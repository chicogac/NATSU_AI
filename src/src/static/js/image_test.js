// Direct image test script that bypasses all existing code
window.addEventListener('DOMContentLoaded', () => {
    console.log("Image test script loaded!");
    
    // Create a button to test images
    const testButton = document.createElement('button');
    testButton.textContent = 'TEST IMAGES DIRECTLY';
    testButton.style.position = 'fixed';
    testButton.style.top = '10px';
    testButton.style.left = '10px';
    testButton.style.zIndex = '9999';
    testButton.style.padding = '10px';
    testButton.style.backgroundColor = 'red';
    testButton.style.color = 'white';
    testButton.style.fontWeight = 'bold';
    testButton.style.border = 'none';
    testButton.style.borderRadius = '5px';
    testButton.style.cursor = 'pointer';
    
    // Add click handler
    testButton.addEventListener('click', () => {
        console.log("Testing images directly...");
        testImagesDirectly();
    });
    
    // Add button to page
    document.body.appendChild(testButton);
    
    // Auto-run test after 2 seconds
    setTimeout(testImagesDirectly, 2000);
});

// Function to test images directly
function testImagesDirectly() {
    console.log("DIRECT IMAGE TEST RUNNING");
    
    // Create test container
    const testContainer = document.createElement('div');
    testContainer.id = 'direct-image-test';
    testContainer.style.position = 'fixed';
    testContainer.style.top = '50%';
    testContainer.style.left = '50%';
    testContainer.style.transform = 'translate(-50%, -50%)';
    testContainer.style.backgroundColor = 'white';
    testContainer.style.padding = '20px';
    testContainer.style.border = '5px solid red';
    testContainer.style.borderRadius = '10px';
    testContainer.style.zIndex = '10000';
    testContainer.style.minWidth = '80%';
    testContainer.style.maxHeight = '80vh';
    testContainer.style.overflow = 'auto';
    testContainer.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';
    
    // Add heading
    const heading = document.createElement('h2');
    heading.textContent = 'DIRECT IMAGE TEST';
    heading.style.color = 'red';
    heading.style.textAlign = 'center';
    heading.style.margin = '0 0 15px 0';
    testContainer.appendChild(heading);
    
    // Add subheading with description
    const subheading = document.createElement('p');
    subheading.textContent = 'This test bypasses all existing code to directly load and display images';
    subheading.style.textAlign = 'center';
    subheading.style.marginBottom = '20px';
    testContainer.appendChild(subheading);
    
    // Add image holder
    const imageHolder = document.createElement('div');
    imageHolder.style.display = 'flex';
    imageHolder.style.flexWrap = 'wrap';
    imageHolder.style.justifyContent = 'center';
    imageHolder.style.gap = '20px';
    testContainer.appendChild(imageHolder);
    
    // Test specific images
    const testImages = [
        'memory_box.jpg',
        'car_packed.jpg',
        'birthday_party.jpg',
        'fireflies.jpg'
    ];
    
    // Process each test image
    testImages.forEach((imageName, index) => {
        // Create image container
        const imageContainer = document.createElement('div');
        imageContainer.style.textAlign = 'center';
        imageContainer.style.border = '1px solid #ddd';
        imageContainer.style.padding = '10px';
        imageContainer.style.borderRadius = '5px';
        imageContainer.style.width = '250px';
        
        // Add image name
        const nameLabel = document.createElement('p');
        nameLabel.textContent = `${index + 1}. ${imageName}`;
        nameLabel.style.margin = '0 0 10px 0';
        nameLabel.style.fontWeight = 'bold';
        imageContainer.appendChild(nameLabel);
        
        // Create image element with detailed logging
        const image = new Image();
        image.src = `/story_images/${imageName}`;
        image.alt = imageName;
        image.style.maxWidth = '100%';
        image.style.border = '1px solid #aaa';
        
        // Status indicator
        const status = document.createElement('div');
        status.textContent = 'Loading...';
        status.style.marginTop = '10px';
        status.style.fontSize = '14px';
        status.style.color = '#777';
        imageContainer.appendChild(status);
        
        // Image load event
        image.onload = function() {
            console.log(`SUCCESS: Image ${imageName} loaded successfully`);
            console.log(`- Dimensions: ${this.naturalWidth}x${this.naturalHeight}`);
            
            status.textContent = `Loaded: ${this.naturalWidth}x${this.naturalHeight}px`;
            status.style.color = 'green';
            
            // Add a clear success border
            image.style.border = '3px solid green';
        };
        
        // Image error event
        image.onerror = function(e) {
            console.error(`FAILED: Image ${imageName} failed to load`);
            console.error(e);
            
            status.textContent = 'Failed to load!';
            status.style.color = 'red';
            
            // Add error styling
            imageContainer.style.border = '2px solid red';
            
            // Try direct fetch to see response
            fetch(`/story_images/${imageName}`)
                .then(response => {
                    console.log(`Fetch status for ${imageName}: ${response.status} ${response.statusText}`);
                    if (response.ok) {
                        status.textContent = `Fetch successful but image failed (${response.status})`;
                    } else {
                        status.textContent = `Server returned: ${response.status} ${response.statusText}`;
                    }
                })
                .catch(err => {
                    status.textContent = `Fetch error: ${err.message}`;
                    console.error(`Fetch error for ${imageName}:`, err);
                });
        };
        
        // Add image to container
        imageContainer.appendChild(image);
        imageHolder.appendChild(imageContainer);
    });
    
    // Add close button
    const closeButton = document.createElement('button');
    closeButton.textContent = 'Close';
    closeButton.style.display = 'block';
    closeButton.style.margin = '20px auto 0';
    closeButton.style.padding = '8px 15px';
    closeButton.style.backgroundColor = '#333';
    closeButton.style.color = 'white';
    closeButton.style.border = 'none';
    closeButton.style.borderRadius = '5px';
    closeButton.style.cursor = 'pointer';
    closeButton.onclick = function() {
        testContainer.remove();
    };
    testContainer.appendChild(closeButton);
    
    // Add container to page
    document.body.appendChild(testContainer);
} 