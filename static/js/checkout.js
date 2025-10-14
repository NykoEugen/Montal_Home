document.addEventListener('DOMContentLoaded', () => {
    const checkoutForm = document.getElementById('checkout-form');
    const cityInput = document.getElementById('city-input');
    const suggestionsList = document.getElementById('city-suggestions');

    const getFieldValue = (name) => {
        if (!checkoutForm) {
            return '';
        }
        const field = checkoutForm.elements.namedItem(name);
        if (!field) {
            return '';
        }
        if (field instanceof HTMLSelectElement) {
            return field.value.trim();
        }
        if (field instanceof RadioNodeList) {
            return field.value.trim();
        }
        return field.value ? field.value.trim() : '';
    };

    const isContactComplete = () => {
        const requiredFields = ['customer_name', 'customer_last_name', 'customer_phone_number'];
        return requiredFields.every((name) => getFieldValue(name).length > 0);
    };

    const isDeliveryComplete = () => {
        const deliveryType = getFieldValue('delivery_type');
        if (!deliveryType) {
            return false;
        }
        if (deliveryType === 'local') {
            return getFieldValue('delivery_address').length > 0;
        }
        if (deliveryType === 'nova_poshta') {
            return getFieldValue('delivery_city_label').length > 0 && getFieldValue('delivery_branch_label').length > 0;
        }
        return false;
    };

    const isPaymentComplete = () => getFieldValue('payment_type').length > 0;

    const stepIndicators = checkoutForm
        ? [
              {
                  key: 'contact',
                  indicator: document.querySelector('[data-step="contact"]'),
                  label: document.querySelector('[data-step-label="contact"]'),
                  isComplete: isContactComplete,
              },
              {
                  key: 'delivery',
                  indicator: document.querySelector('[data-step="delivery"]'),
                  label: document.querySelector('[data-step-label="delivery"]'),
                  isComplete: isDeliveryComplete,
              },
              {
                  key: 'payment',
                  indicator: document.querySelector('[data-step="payment"]'),
                  label: document.querySelector('[data-step-label="payment"]'),
                  isComplete: isPaymentComplete,
              },
              {
                  key: 'confirm',
                  indicator: document.querySelector('[data-step="confirm"]'),
                  label: document.querySelector('[data-step-label="confirm"]'),
                  isComplete: () => isContactComplete() && isDeliveryComplete() && isPaymentComplete(),
              },
          ]
        : [];

    const stepState = new Map(stepIndicators.map((step) => [step.key, false]));

    const triggerStepAnimation = (element) => {
        if (!element) {
            return;
        }
        element.classList.remove('animate-step');
        // Force reflow to restart animation
        // eslint-disable-next-line no-unused-expressions
        element.offsetWidth;
        element.classList.add('animate-step');
        element.addEventListener(
            'animationend',
            () => {
                element.classList.remove('animate-step');
            },
            { once: true }
        );
    };

    const updateStepStates = () => {
        if (!checkoutForm || !stepIndicators.length) {
            return;
        }

        const completionChecks = {
            contact: isContactComplete(),
            delivery: isDeliveryComplete(),
            payment: isPaymentComplete(),
            confirm: isContactComplete() && isDeliveryComplete() && isPaymentComplete(),
        };

        stepIndicators.forEach((step) => {
            const indicator = step.indicator;
            const label = step.label;
            const isComplete = completionChecks[step.key];
            const wasComplete = stepState.get(step.key);

            if (indicator) {
                indicator.classList.toggle('completed', isComplete);
                indicator.classList.remove('active');
                if (isComplete && !wasComplete) {
                    triggerStepAnimation(indicator);
                }
            }

            if (label) {
                label.classList.toggle('completed', isComplete);
                label.classList.remove('active');
            }

            stepState.set(step.key, isComplete);
        });

        let activeAssigned = false;
        for (const step of stepIndicators) {
            if (!step.indicator) {
                continue;
            }
            if (stepState.get(step.key)) {
                continue;
            }
            if (!activeAssigned) {
                step.indicator.classList.add('active');
                if (step.label) {
                    step.label.classList.add('active');
                }
                activeAssigned = true;
            }
        }

        if (!activeAssigned && stepIndicators.length) {
            const finalStep = stepIndicators[stepIndicators.length - 1];
            if (finalStep.indicator) {
                finalStep.indicator.classList.add('active');
            }
            if (finalStep.label) {
                finalStep.label.classList.add('active');
            }
        }
    };

    if (checkoutForm && stepIndicators.length) {
        checkoutForm.addEventListener('input', updateStepStates);
        checkoutForm.addEventListener('change', updateStepStates);
    }

    if (cityInput && suggestionsList) {
        let debounceTimeout = null;

        cityInput.addEventListener('input', function () {
            const query = this.value.trim();
            clearTimeout(debounceTimeout);

            if (query.length < 2) {
                suggestionsList.classList.add('hidden');
                return;
            }

            debounceTimeout = setTimeout(() => {
                fetch(`/delivery/np/cities?q=${encodeURIComponent(query)}`)
                    .then((res) => res.json())
                    .then((data) => {
                        suggestionsList.innerHTML = '';

                        if (!data.length) {
                            suggestionsList.classList.add('hidden');
                            return;
                        }

                        data.forEach((city) => {
                            const item = document.createElement('li');
                            item.textContent = city.label;
                            item.dataset.ref = city.ref;
                            item.classList.add('px-2', 'py-1', 'hover:bg-gray-100', 'cursor-pointer');

                            item.addEventListener('click', () => {
                                cityInput.value = city.label;
                                suggestionsList.innerHTML = '';
                                suggestionsList.classList.add('hidden');

                                const deliveryCityInput = document.querySelector('[name="delivery_city"]');
                                if (deliveryCityInput) {
                                    deliveryCityInput.value = city.ref;
                                }

                                const cityNameInput = document.querySelector('[name="delivery_city_name"]');
                                if (cityNameInput) {
                                    cityNameInput.value = city.label;
                                }

                                const warehouseSelect = document.getElementById('warehouse-select');
                                if (warehouseSelect) {
                                    warehouseSelect.innerHTML = '<option value="">Завантаження відділень...</option>';

                                    fetch(`/delivery/np/warehouses?city_ref=${city.ref}`)
                                        .then((res) => res.json())
                                        .then((warehouses) => {
                                            const branchHiddenInput = document.querySelector('[name="delivery_branch"]');
                                            if (branchHiddenInput) {
                                                branchHiddenInput.value = '';
                                            }

                                            warehouseSelect.innerHTML = '<option value="">Оберіть відділення</option>';
                                            warehouseSelect.selectedIndex = 0;

                                            if (!warehouses.length) {
                                                warehouseSelect.innerHTML = '<option value="">Відділень не знайдено</option>';
                                                updateStepStates();
                                                return;
                                            }

                                            warehouses.forEach((wh) => {
                                                const option = document.createElement('option');
                                                option.value = wh.ref;
                                                option.textContent = wh.label;
                                                warehouseSelect.appendChild(option);
                                            });

                                            warehouseSelect.onchange = () => {
                                                const selectedOption = warehouseSelect.options[warehouseSelect.selectedIndex];
                                                const branchHiddenInput = document.querySelector('[name="delivery_branch"]');
                                                if (branchHiddenInput) {
                                                    branchHiddenInput.value = selectedOption.value;
                                                }

                                                const branchNameInput = document.querySelector('[name="delivery_branch_name"]');
                                                if (branchNameInput) {
                                                    branchNameInput.value = selectedOption.textContent;
                                                }

                                                updateStepStates();
                                            };

                                            updateStepStates();
                                        })
                                        .catch((error) => {
                                            console.error('Error loading warehouses:', error);
                                            warehouseSelect.innerHTML = '<option value="">Помилка завантаження</option>';
                                            updateStepStates();
                                        });
                                } else {
                                    console.error('Warehouse select element not found');
                                }

                                updateStepStates();
                            });

                            suggestionsList.appendChild(item);
                        });

                        suggestionsList.classList.remove('hidden');
                    })
                    .catch(() => {
                        suggestionsList.classList.add('hidden');
                    });
            }, 300);
        });

        document.addEventListener('click', (event) => {
            if (!cityInput.contains(event.target) && !suggestionsList.contains(event.target)) {
                suggestionsList.classList.add('hidden');
            }
        });
    }

    updateStepStates();
});
