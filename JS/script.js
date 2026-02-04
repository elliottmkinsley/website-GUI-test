/**
 * Core Application Logic
 * Handles interactive elements: slider, sticky header navigation, mobile menu, and scroll animations.
 * * Architecture Note:
 * Logic is encapsulated within 'DOMContentLoaded' to ensure DOM readiness.
 * IntersectionObservers are used for performance-critical scroll effects instead of scroll event listeners where possible.
 */

/**
 * Horizontal scroll handler for equipment cards.
 * Uses native smooth scroll API for better performance than custom animation loops.
 * @param {number} amount - Pixel value to scroll (positive=right, negative=left)
 */
function scrollGrid(amount) {
    const container = document.getElementById('cardContainer');
    if (container) {
        container.scrollBy({ left: amount, behavior: 'smooth' });
    }
}

/**
 * Equipment Catalog Scroll Alias
 * Provides a semantic alias for the catalog page while reusing the same underlying logic.
 */
function scrollCatalog(amount) {
    scrollGrid(amount);
}

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------------------
    // Sticky Header Logic
    // Toggles 'scrolled' class based on scroll position for glassmorphism effect.
    // -------------------------------------------------------------------------
    const header = document.getElementById('mainHeader');
    if (header) {
        window.addEventListener('scroll', () => {
            // Optimization: Simple check avoids frequent layout thrashing
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
    }

    // -------------------------------------------------------------------------
    // Hero Slider Component
    // Manual implementation of a carousel.
    // -------------------------------------------------------------------------
    const slides = document.querySelectorAll('.slide');
    const nextBtn = document.getElementById('nextSlide');
    const prevBtn = document.getElementById('prevSlide');

    if (slides.length > 1) {
        let currentSlide = 0;
        const totalSlides = slides.length;
        let slideInterval;

        function showSlide(index) {
            if (index >= totalSlides) index = 0;
            if (index < 0) index = totalSlides - 1;

            // Remove active class from current, update index, add to new
            slides[currentSlide].classList.remove('active');
            currentSlide = index;
            slides[currentSlide].classList.add('active');
        }

        // Navigation Wrappers
        function nextSlide() { showSlide(currentSlide + 1); }
        function prevSlide() { showSlide(currentSlide - 1); }

        if (nextBtn && prevBtn) {
            nextBtn.addEventListener('click', () => { nextSlide(); resetInterval(); });
            prevBtn.addEventListener('click', () => { prevSlide(); resetInterval(); });
        }

        // Auto-advance logic
        function startInterval() { slideInterval = setInterval(nextSlide, 6000); }
        function resetInterval() { clearInterval(slideInterval); startInterval(); }

        // Init Slider
        startInterval();
    }

    // Featured Equipment Carousel (Homepage)
    // Connects the Left/Right arrows to the scroll logic
    // -------------------------------------------------------------------------
    const carouselLeft = document.querySelector('.nav-btn.left');
    const carouselRight = document.querySelector('.nav-btn.right');

    if (carouselLeft && carouselRight) {
        carouselLeft.addEventListener('click', () => {
            scrollGrid(-350); // Scroll Left
        });

        carouselRight.addEventListener('click', () => {
            scrollGrid(350); // Scroll Right
        });
    }

    // Integrated Education Paths Carousel
    // -------------------------------------------------------------------------
    const eduLeft = document.getElementById('eduLeft');
    const eduRight = document.getElementById('eduRight');
    const eduContainer = document.getElementById('educationContainer');

    if (eduLeft && eduRight && eduContainer) {
        eduLeft.addEventListener('click', () => {
            eduContainer.scrollBy({ left: -360, behavior: 'smooth' });
        });

        eduRight.addEventListener('click', () => {
            eduContainer.scrollBy({ left: 360, behavior: 'smooth' });
        });
    }

    // -------------------------------------------------------------------------
    // Mobile Navigation Toggle
    // Handles the mobile menu overlay state.
    // -------------------------------------------------------------------------
    const mobileBtn = document.querySelector('.mobile-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileBtn && navMenu) {
        mobileBtn.addEventListener('click', () => {
            const isHidden = window.getComputedStyle(navMenu).display === 'none';
            if (isHidden) {
                // Force flex display for mobile overlay
                Object.assign(navMenu.style, {
                    display: 'flex',
                    flexDirection: 'column',
                    position: 'absolute',
                    top: '100%',
                    left: '0',
                    width: '100%',
                    background: 'var(--nau-blue)',
                    padding: '20px',
                    zIndex: '1000'
                });
            } else {
                navMenu.style.display = 'none';
                // Reset inline style if viewport resized
                if (window.innerWidth > 1024) navMenu.style.display = '';
            }
        });
    }

    // -------------------------------------------------------------------------
    // Scroll Animation Observer (Progressive Enhancement)
    // Uses IntersectionObserverAPI to trigger '.fade-in' animations.
    // -------------------------------------------------------------------------
    const cards = document.querySelectorAll('.card, .featured-story, .player-card, .metric-box');

    // Fallback: If JS fails or Observer not supported, force reveal after delay
    setTimeout(() => {
        cards.forEach(card => {
            if (getComputedStyle(card).opacity === '0') {
                card.style.opacity = '1';
            }
        });
    }, 1500);

    if ('IntersectionObserver' in window) {
        const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target); // Run once per element
                }
            });
        }, observerOptions);

        cards.forEach(card => {
            card.style.opacity = '0'; // Initial state for animation
            observer.observe(card);
        });
    }

    // -------------------------------------------------------------------------
    // Animated Statistics Counter
    // -------------------------------------------------------------------------
    const stats = document.querySelectorAll('.metric-value');
    if (stats.length > 0) {
        const animateValue = (obj, start, end, duration) => {
            let startTimestamp = null;
            const step = (timestamp) => {
                if (!startTimestamp) startTimestamp = timestamp;
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                // EaseOutExpo effect
                const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
                let value = Math.floor(easeProgress * (end - start) + start);

                if (obj.dataset.suffix) value += obj.dataset.suffix;
                if (obj.dataset.prefix) value = obj.dataset.prefix + value;

                obj.innerHTML = value;

                if (progress < 1) {
                    window.requestAnimationFrame(step);
                }
            };
            window.requestAnimationFrame(step);
        }

        const statsObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const target = entry.target;
                    const rawText = target.innerText;
                    let prefix = rawText.includes('$') ? '$' : '';
                    let suffix = rawText.includes('%') ? '%' : (rawText.includes('+') ? '+' : '');
                    let endValue = parseInt(rawText.replace(/[^0-9]/g, ''));

                    if (!isNaN(endValue)) {
                        target.dataset.prefix = prefix;
                        target.dataset.suffix = suffix;
                        animateValue(target, 0, endValue, 2000);
                    }
                    observer.unobserve(target);
                }
            });
        }, { threshold: 0.5 });

        stats.forEach(stat => {
            statsObserver.observe(stat);
        });
    }

    // -------------------------------------------------------------------------
    // Contact Form Handler
    // -------------------------------------------------------------------------
    const contactForm = document.querySelector('form');
    if (contactForm && contactForm.id === 'contactForm') {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Thank you for your message! We will get back to you shortly.');
            contactForm.reset();
        });
    }

    // -------------------------------------------------------------------------
    // Equipment Catalog Logic: Filtering & View Layout
    // -------------------------------------------------------------------------
    const filterBtns = document.querySelectorAll('.filter-btn');
    const searchInput = document.getElementById('searchInput');
    const eqCards = document.querySelectorAll('.equipment-card');

    // View Switcher Elements
    const gridBtn = document.getElementById('gridViewBtn');
    const listBtn = document.getElementById('listViewBtn');
    const container = document.getElementById('cardContainer');
    const arrows = document.querySelectorAll('.nav-btn');

    if (filterBtns.length > 0) {

        // A. View Toggle Logic (Grid vs List)
        if (gridBtn && listBtn && container) {
            // Switch to List View
            listBtn.addEventListener('click', () => {
                container.classList.add('list-view');
                listBtn.classList.add('active');
                gridBtn.classList.remove('active');
                // Hide arrows in list view (vertical layout)
                arrows.forEach(arrow => arrow.style.display = 'none');
            });

            // Switch to Grid View
            gridBtn.addEventListener('click', () => {
                container.classList.remove('list-view');
                gridBtn.classList.add('active');
                listBtn.classList.remove('active');
                // Show arrows in grid view (carousel layout)
                arrows.forEach(arrow => arrow.style.display = 'flex');
            });
        }

        // B. Filtering Logic
        const filterItems = () => {
            const term = searchInput ? searchInput.value.toLowerCase() : '';
            const activeBtn = document.querySelector('.filter-btn.active');
            const activeCategory = activeBtn ? activeBtn.dataset.filter : 'all';

            eqCards.forEach(card => {
                const title = card.dataset.title ? card.dataset.title.toLowerCase() : '';
                const categories = card.dataset.category ? card.dataset.category.toLowerCase() : '';

                const matchesSearch = title.includes(term);
                // Use includes() to support multi-tagged items
                const matchesCategory = activeCategory === 'all' || categories.includes(activeCategory);

                if (matchesSearch && matchesCategory) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        };

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                filterItems();
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', filterItems);
        }

        // Check URL Params for direct category linking
        const urlParams = new URLSearchParams(window.location.search);
        const categoryParam = urlParams.get('category');
        if (categoryParam) {
            const targetBtn = document.querySelector(`.filter-btn[data-filter="${categoryParam}"]`);
            if (targetBtn) {
                targetBtn.click();
            }
        }
    }
});

/**
 * Contact Page Logic (Contact_Us.html)
 * Data structure and functions for dynamic form generation.
 * -------------------------------------------------------------------------
 */
const fieldData = {
    'equipment': {
        title: "Equipment Inquiry",
        desc: "Check availability or request specs for specific tools.",
        fields: `
            <div class="grid grid-2 gap-lg">
                <div>
                    <label class="block font-bold mb-1 required">Equipment of Interest</label>
                    <select class="form-control">
                        <option>-- Select Tool --</option>
                        <option>Keyence VHX-7000</option>
                        <option>B-2 AFM</option>
                        <option>JEOL TEM</option>
                        <option>Mask Aligner</option>
                        <option>Other / Unsure</option>
                    </select>
                </div>
                <div>
                    <label class="block font-bold mb-1">Intended Usage</label>
                    <select class="form-control">
                        <option>Self-Use (I need training)</option>
                        <option>Service (Staff runs samples)</option>
                    </select>
                </div>
                <div class="col-span-2">
                    <label class="block font-bold mb-1 required">Technical Requirements</label>
                    <textarea rows="3" class="form-control" placeholder="Describe sample type, size, and measurement goals..."></textarea>
                </div>
            </div>
        `
    },
    'research': {
        title: "Research Collaboration",
        desc: "Propose a joint project or grant partnership.",
        fields: `
            <div class="form-stack">
                <div>
                    <label class="block font-bold mb-1 required">Project Title / Topic</label>
                    <input type="text" class="form-control" placeholder="e.g. Novel Dielectric Characterization">
                </div>
                <div class="grid grid-2 gap-lg">
                    <div>
                        <label class="block font-bold mb-1">Funding Agency</label>
                        <input type="text" class="form-control" placeholder="NSF, DOE, Industry...">
                    </div>
                    <div>
                        <label class="block font-bold mb-1">Timeline</label>
                        <select class="form-control">
                            <option>Short Term (< 3 months)</option>
                            <option>Long Term (1+ year)</option>
                            <option>Grant Proposal Phase</option>
                        </select>
                    </div>
                </div>
                <div>
                    <label class="block font-bold mb-1 required">Project Abstract</label>
                    <textarea rows="5" class="form-control" placeholder="Provide a brief summary of the research goals..."></textarea>
                </div>
            </div>
        `
    },
    'billing': {
        title: "Billing & Invoicing",
        desc: "Resolve payment issues or request quotes.",
        fields: `
            <div class="grid grid-2 gap-lg">
                <div>
                    <label class="block font-bold mb-1 required">Reference Number</label>
                    <input type="text" class="form-control" placeholder="Invoice # or PO #">
                </div>
                <div>
                    <label class="block font-bold mb-1 required">Billing Contact Person</label>
                    <input type="text" class="form-control">
                </div>
                <div class="col-span-2">
                    <label class="block font-bold mb-1">Billing Address</label>
                    <textarea rows="2" class="form-control"></textarea>
                </div>
                <div class="col-span-2">
                    <label class="block font-bold mb-1">Issue Description</label>
                    <textarea rows="3" class="form-control" placeholder="Describe the billing discrepancy or request..."></textarea>
                </div>
            </div>
        `
    },
    'training': {
        title: "Safety & Training",
        desc: "Register for safety courses or equipment authorization.",
        fields: `
            <div class="grid grid-2 gap-lg">
                <div>
                    <label class="block font-bold mb-1 required">Current Status</label>
                    <select class="form-control">
                        <option>New User (No Access)</option>
                        <option>Active User (Adding Tool)</option>
                        <option>Expired Access (Renewal)</option>
                    </select>
                </div>
                <div>
                    <label class="block font-bold mb-1 required">Requested Training</label>
                    <select class="form-control">
                        <option>EHS Basic Safety (Mandatory)</option>
                        <option>Cleanroom Gowning</option>
                        <option>Chemical Safety</option>
                        <option>Specific Tool Authorization</option>
                    </select>
                </div>
                <div>
                    <label class="block font-bold mb-1">NAU ID</label>
                    <input type="text" class="form-control" placeholder="1234567">
                </div>
                <div>
                    <label class="block font-bold mb-1">PI / Supervisor Name</label>
                    <input type="text" class="form-control">
                </div>
            </div>
        `
    },
    'courses': {
        title: "Course Support",
        desc: "Inquiries regarding lab classes or curriculum.",
        fields: `
            <div class="grid grid-2 gap-lg">
                <div>
                    <label class="block font-bold mb-1 required">Course Number</label>
                    <input type="text" class="form-control" placeholder="e.g. EE400">
                </div>
                <div>
                    <label class="block font-bold mb-1">Semester</label>
                    <select class="form-control">
                        <option>Fall 2025</option>
                        <option>Spring 2026</option>
                        <option>Summer 2026</option>
                    </select>
                </div>
                <div class="col-span-2">
                    <label class="block font-bold mb-1 required">Inquiry</label>
                    <textarea rows="3" class="form-control" placeholder="Question about lab schedule, materials, or enrollment..."></textarea>
                </div>
            </div>
        `
    },
    'tour': {
        title: "Schedule a Tour",
        desc: "Visit the facility.",
        fields: `
            <div class="grid grid-2 gap-lg">
                <div>
                    <label class="block font-bold mb-1 required">Group Size</label>
                    <input type="number" class="form-control" placeholder="Approx number of people">
                </div>
                <div>
                    <label class="block font-bold mb-1 required">Group Type</label>
                    <select class="form-control">
                        <option>K-12 School</option>
                        <option>Prospective Students</option>
                        <option>Industry Partners</option>
                        <option>Academic Guests</option>
                    </select>
                </div>
                <div>
                    <label class="block font-bold mb-1 required">Preferred Date</label>
                    <input type="date" class="form-control">
                </div>
                <div>
                    <label class="block font-bold mb-1">Alternative Date</label>
                    <input type="date" class="form-control">
                </div>
            </div>
        `
    },
    'sales': {
        title: "Vendor / Sales",
        desc: "Product demonstrations and supply chain.",
        fields: `
            <div class="form-stack">
                <div>
                    <label class="block font-bold mb-1 required">Product Category</label>
                    <input type="text" class="form-control" placeholder="e.g. Chemicals, Metrology Equipment, PPE">
                </div>
                <div>
                    <label class="block font-bold mb-1 required">Message</label>
                    <textarea rows="4" class="form-control" placeholder="Describe your product or reason for contact..."></textarea>
                </div>
            </div>
        `
    },
    'other': {
        title: "General Inquiry",
        desc: "How can we help you?",
        fields: `
            <div>
                <label class="block font-bold mb-1 required">Message</label>
                <textarea rows="5" class="form-control" placeholder="Please describe your question or issue..."></textarea>
            </div>
        `
    }
};

function selectCategory(category, element) {
    // Highlighting Logic
    document.querySelectorAll('.gateway-card').forEach(card => card.classList.remove('selected'));
    element.classList.add('selected');

    // Data Injection
    const data = fieldData[category];
    const formContainer = document.getElementById('formContainer');
    const dynamicFields = document.getElementById('dynamicFields');
    const formTitle = document.getElementById('formTitle');
    const formDesc = document.getElementById('formDesc');

    if (data) {
        formTitle.textContent = data.title;
        formDesc.textContent = data.desc;
        dynamicFields.innerHTML = data.fields;
        dynamicFields.className = 'fade-in';

        // Show Form
        formContainer.classList.remove('hidden');
        void formContainer.offsetWidth;
        formContainer.classList.add('fade-in');

        // Smooth Scroll
        setTimeout(() => {
            formContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }
}

function resetSelection() {
    document.querySelectorAll('.gateway-card').forEach(card => card.classList.remove('selected'));
    document.getElementById('formContainer').classList.add('hidden');
    document.getElementById('formContainer').classList.remove('fade-in');
    document.getElementById('gatewayGrid').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function handleFormSubmit(e) {
    e.preventDefault();
    alert("Thank you! Your inquiry has been routed to the appropriate team.");
    resetSelection();
    document.getElementById('contactForm').reset();
}

// Global Exports
window.fieldData = fieldData;
window.selectCategory = selectCategory;
window.resetSelection = resetSelection;
window.handleFormSubmit = handleFormSubmit;


// -------------------------------------------------------------------------
// EQUIPMENT CATALOG LOGIC
// Handles Grid/List toggle and Category Filtering
// -------------------------------------------------------------------------
const container = document.getElementById('equipmentContainer');
const gridBtn = document.getElementById('gridViewBtn');
const listBtn = document.getElementById('listViewBtn');
const filterBtns = document.querySelectorAll('.filter-btn');
const cards = document.querySelectorAll('.tech-card');

// 1. VIEW SWITCHER (Grid vs List)
if (container && gridBtn && listBtn) {
    gridBtn.addEventListener('click', () => {
        container.classList.remove('list-layout');
        container.classList.add('grid-layout');
        gridBtn.classList.add('active');
        listBtn.classList.remove('active');
    });

    listBtn.addEventListener('click', () => {
        container.classList.remove('grid-layout');
        container.classList.add('list-layout');
        listBtn.classList.add('active');
        gridBtn.classList.remove('active');
    });
}

// 2. FILTERING LOGIC
if (filterBtns.length > 0) {
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons
            filterBtns.forEach(b => b.classList.remove('active'));
            // Add active to clicked button
            btn.classList.add('active');

            const filterValue = btn.getAttribute('data-filter');

            cards.forEach(card => {
                const category = card.getAttribute('data-category');

                if (filterValue === 'all' || category === filterValue) {
                    card.style.display = 'flex'; // Show
                } else {
                    card.style.display = 'none'; // Hide
                }
            });
        });
    });
}