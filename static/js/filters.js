function toggleDropdown(labelElement) {
        const options = labelElement.nextElementSibling;
        if (options.style.display === "block") {
            options.style.display = "none";
        } else {
            options.style.display = "block";
        }
    }