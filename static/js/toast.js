function showToast(type, message, duration = 5000) {
    // Create a unique ID
    const toastId = "toast-" + Date.now() + "-" + Math.floor(Math.random() * 10000);

    // Define the icon path dynamically based on the toast type
    const iconPath = `/static/assets/${type}.svg`;  // Replace 'static/icons/' with your actual file path

    // Create the toast
    const toast = Toastify({
        text: `
            <div class="toast-content" id="${toastId}">
                <img class="toast-icon" src="${iconPath}" alt="${type} icon" />
                <div class="toast-text">
                    <div class="toast-title">${message.title}</div>
                    <div class="toast-sub">${message.subtitle}</div>
                </div>
                <button class="toast-close-btn" onclick="closeToast('${toastId}')">&times;</button>
            </div>
        `,
        duration: duration,
        close: false, // Disable automatic close button from Toastify (we'll use our own)
        gravity: "top",
        position: "right",
        escapeMarkup: false, // allow HTML (for our ID)
        className: `toast-${type} on-light` // Dynamically apply class based on type
    });

    // Show the toast
    toast.showToast();

    // Wait until it's rendered in DOM
    setTimeout(() => {
        const el = document.getElementById(toastId)?.closest(".toastify");
        if (el) {
            const bar = document.createElement("div");
            bar.classList.add("toast-progress");
            bar.style.animation = `toast-progress ${duration}ms linear forwards`;
            el.appendChild(bar);
        }
    }, 30);
}

// Function to manually close the toast
function closeToast(toastId) {
    const toastElement = document.getElementById(toastId)?.closest(".toastify");
    if (toastElement) {
        toastElement.style.opacity = '0';
        setTimeout(() => {
            toastElement.remove();
        }, 300); // Match the fade-out duration
    }
}


// Convenience wrappers
function toastSuccess(title, subtitle) { showToast("success", {title, subtitle}, 5000); }
function toastError(title, subtitle)   { showToast("error", {title, subtitle}, 5000); }
function toastInfo(title, subtitle)    { showToast("info", {title, subtitle}, 5000); }
function toastAlert(title, subtitle)   { showToast("alert", {title, subtitle}, 5000); }

