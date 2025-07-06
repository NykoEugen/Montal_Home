document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById("city-input");
    const list = document.getElementById("city-suggestions");

    let debounceTimeout = null;

    input.addEventListener("input", function () {
        const query = this.value.trim();
        clearTimeout(debounceTimeout);

        if (query.length < 2) {
            list.classList.add("hidden");
            return;
        }

        debounceTimeout = setTimeout(() => {
            fetch(`/delivery/np/cities?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    list.innerHTML = "";

                    if (!data.length) {
                        list.classList.add("hidden");
                        return;
                    }

                    data.forEach(city => {
                        const item = document.createElement("li");
                        item.textContent = city.label;
                        item.dataset.ref = city.ref;
                        item.classList.add("px-2", "py-1", "hover:bg-gray-100", "cursor-pointer");

                        item.onclick = () => {
                            input.value = city.label;
                            list.innerHTML = "";
                            list.classList.add("hidden");

                            document.querySelector('[name="delivery_city"]').value = city.ref;

                            let cityNameInput = document.querySelector('[name="delivery_city_name"]');
                            if (cityNameInput) cityNameInput.value = city.label;

                            // Очистити список відділень
                            const warehouseSelect = document.getElementById("warehouse-select");
                            warehouseSelect.innerHTML = '<option value="">Завантаження відділень...</option>';

                            // Завантажити відділення
                            fetch(`/delivery/np/warehouses?city_ref=${city.ref}`)
                                .then(res => res.json())
                                .then(data => {
                                    const branchHiddenInput = document.querySelector('[name="delivery_branch"]');
                                    branchHiddenInput.value = "";

                                    warehouseSelect.innerHTML = ""; // Очистити перед додаванням

                                    if (!data.length) {
                                        warehouseSelect.innerHTML = '<option value="">Відділень не знайдено</option>';
                                        return;
                                    }

                                    data.forEach(wh => {
                                        const option = document.createElement("option");
                                        option.value = wh.ref;
                                        option.textContent = wh.label;
                                        warehouseSelect.appendChild(option);
                                    });

                                    warehouseSelect.onchange = () => {
                                        let selectedOption = warehouseSelect.options[warehouseSelect.selectedIndex];
                                        document.querySelector('[name="delivery_branch"]').value = selectedOption.value;

                                        let branchNameInput = document.querySelector('[name="delivery_branch_name"]');
                                        if (branchNameInput) branchNameInput.value = selectedOption.textContent;
                                    };
                                });
                        };

                        list.appendChild(item);
                    });

                    list.classList.remove("hidden");
                });
        }, 300); // debounce
    });

    // При кліку поза полем — ховаємо список
    document.addEventListener("click", (e) => {
        if (!input.contains(e.target) && !list.contains(e.target)) {
            list.classList.add("hidden");
        }
    });
});