/**
 * Core Application Logic
 * Handles interactive elements: slider, sticky header navigation, mobile menu, and scroll animations.
 * * Architecture Note:
 * Logic is encapsulated within 'DOMContentLoaded' to ensure DOM readiness.
 * IntersectionObservers are used for performance-critical scroll effects instead of scroll event listeners where possible.
 */

/**
 * Horizontal scroll handler for card lists.
 * Uses native smooth scroll API for better performance than custom animation loops.
 * @param {number} amount - Pixel value to scroll (positive=right, negative=left)
 */
function scrollGrid(amount) {
    const container = document.getElementById('cardContainer');
    if (container) {
        container.scrollBy({ left: amount, behavior: 'smooth' });
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const slugify = (value) => {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/['"]/g, '')
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
    };

    const getMeaningfulNameParts = (fullName) => {
        const titlePrefixes = new Set(['dr', 'prof', 'professor', 'mr', 'mrs', 'ms', 'miss']);
        const cleaned = String(fullName || '').replace(/\s+/g, ' ').trim();
        if (!cleaned) return [];

        const parts = cleaned
            .split(' ')
            .map((part) => part
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '')
                .replace(/[^a-zA-Z0-9-]/g, ''))
            .filter(Boolean);

        let startIndex = 0;
        while (startIndex < parts.length && titlePrefixes.has(parts[startIndex].toLowerCase())) {
            startIndex += 1;
        }

        return parts.slice(startIndex);
    };

    const personKeyFromName = window.TeamData?.personKeyFromName || ((fullName) => {
        const parts = getMeaningfulNameParts(fullName);
        if (parts.length < 2) return null;

        const firstName = parts[0];
        const lastName = parts[parts.length - 1];
        return `${slugify(firstName)}-${slugify(lastName)}`;
    });

    const dataRenderTasks = [];
    if (window.TeamData?.renderPageData) {
        dataRenderTasks.push(window.TeamData.renderPageData());
    }
    if (window.ProjectData?.renderPageData) {
        dataRenderTasks.push(window.ProjectData.renderPageData());
    }
    if (dataRenderTasks.length) {
        await Promise.all(dataRenderTasks);
    }

    // Auto-assign anchor ids on Our Team page
    if (document.querySelector('.team-page')) {
        const legacyPersonKeysFromName = window.TeamData?.legacyPersonKeysFromName || ((fullName) => {
            const cleaned = String(fullName || '').replace(/\s+/g, ' ').trim();
            if (!cleaned) return [];

            const parts = cleaned
                .split(' ')
                .map((part) => part
                    .normalize('NFD')
                    .replace(/[\u0300-\u036f]/g, '')
                    .replace(/[^a-zA-Z0-9-]/g, ''))
                .filter(Boolean);

            if (parts.length < 2) return [];

            const firstPart = parts[0];
            const lastPart = parts[parts.length - 1];
            const legacyKey = `${slugify(firstPart)}-${slugify(lastPart?.[0] || '')}`;
            const modernKey = personKeyFromName(fullName);
            return [legacyKey, modernKey].filter((key, index, allKeys) => key && allKeys.indexOf(key) === index);
        });

        document.querySelectorAll('.person-feature').forEach((card) => {
            const name = card.querySelector('.person-name')?.textContent;
            const key = personKeyFromName(name);
            const legacyKeys = legacyPersonKeysFromName(name);

            if (key && !card.id) {
                card.id = key;
            }
            if (key) {
                card.dataset.personKey = key;
            }
            if (legacyKeys.length) {
                card.dataset.personLegacyKeys = legacyKeys.join('|');
            }
        });

        const resolveTeamHashTarget = (targetId) => {
            if (!targetId) return null;

            const directTarget = document.getElementById(targetId);
            if (directTarget) return directTarget;

            return Array.from(document.querySelectorAll('.person-feature')).find((card) => {
                const aliases = (card.dataset.personLegacyKeys || '')
                    .split('|')
                    .map((value) => value.trim())
                    .filter(Boolean);
                return card.dataset.personKey === targetId || aliases.includes(targetId);
            }) || null;
        };

        const waitForTeamImages = () => {
            const teamImages = Array.from(document.querySelectorAll('.person-feature img'));
            if (!teamImages.length) {
                return Promise.resolve();
            }

            return Promise.all(teamImages.map((img) => {
                if (img.complete) {
                    return Promise.resolve();
                }

                return new Promise((resolve) => {
                    img.addEventListener('load', resolve, { once: true });
                    img.addEventListener('error', resolve, { once: true });
                });
            }));
        };

        const scrollTargetToTop = (target, behavior = 'auto') => {
            if (!target) return;
            const headerHeight = document.querySelector('.site-header')?.getBoundingClientRect().height || 0;
            const top = target.getBoundingClientRect().top + window.scrollY - headerHeight - 16;
            window.scrollTo({ top: Math.max(0, Math.round(top)), behavior });
        };

        const scrollToTeamHashTarget = async (behavior = 'auto') => {
            const rawHash = window.location.hash;
            if (!rawHash || rawHash.length < 2) return;

            const targetId = decodeURIComponent(rawHash.slice(1));
            const target = resolveTeamHashTarget(targetId);
            if (!target) return;

            await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            scrollTargetToTop(target, behavior);

            window.setTimeout(() => scrollTargetToTop(target, behavior), 180);
            waitForTeamImages().then(() => {
                window.setTimeout(() => scrollTargetToTop(target, behavior), 0);
            });
        };

        if ('scrollRestoration' in window.history) {
            window.history.scrollRestoration = 'manual';
        }

        scrollToTeamHashTarget();
        window.addEventListener('load', () => scrollToTeamHashTarget());
        window.addEventListener('hashchange', () => scrollToTeamHashTarget());
    }

    // -------------------------------------------------------------------------
    // Carousel Arrow Buttons (Homepage sections)
    // Scrolls by exactly one card at a time.
    // -------------------------------------------------------------------------
    const getCarouselStep = (container) => {
        const card = container.querySelector('.profile-card');
        if (!card) return 350;

        const cardWidth = card.getBoundingClientRect().width || 350;
        const styles = window.getComputedStyle(container);
        const gapValue = styles.gap || styles.columnGap || '0';
        const gap = Number.parseFloat(gapValue) || 0;

        return Math.max(1, Math.round(cardWidth + gap));
    };

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
        let dotButtons = [];

        function showSlide(index) {
            if (index >= totalSlides) index = 0;
            if (index < 0) index = totalSlides - 1;

            // Remove active class from current, update index, add to new
            slides[currentSlide].classList.remove('active');
            currentSlide = index;
            slides[currentSlide].classList.add('active');

            if (dotButtons.length) {
                dotButtons.forEach((btn, i) => {
                    const isActive = i === currentSlide;
                    btn.classList.toggle('active', isActive);
                    btn.setAttribute('aria-current', isActive ? 'true' : 'false');
                    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
                });
            }
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

        // Dot indicators (click to jump)
        const sliderControls = document.querySelector('#heroSlider .slider-controls');
        if (sliderControls) {
            const dotsWrap = document.createElement('div');
            dotsWrap.className = 'slider-dots';
            dotsWrap.setAttribute('role', 'group');
            dotsWrap.setAttribute('aria-label', 'Hero slider navigation');

            dotButtons = Array.from({ length: totalSlides }, (_, i) => {
                const dot = document.createElement('button');
                dot.type = 'button';
                dot.className = 'slider-dot';
                dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
                dot.setAttribute('aria-current', i === currentSlide ? 'true' : 'false');
                dot.setAttribute('aria-pressed', i === currentSlide ? 'true' : 'false');
                dot.addEventListener('click', () => {
                    showSlide(i);
                    resetInterval();
                });
                dotsWrap.appendChild(dot);
                return dot;
            });

            dotButtons[currentSlide]?.classList.add('active');
            const nextButton = sliderControls.querySelector('#nextSlide');
            if (nextButton) {
                sliderControls.insertBefore(dotsWrap, nextButton);
            } else {
                sliderControls.appendChild(dotsWrap);
            }
        }

        // Init Slider
        startInterval();
    }

    // Homepage card carousel controls
    // Connects the Left/Right arrows to the scroll logic
    // -------------------------------------------------------------------------
    document.querySelectorAll('.nav-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const targetId = btn.dataset.target;
          if (!targetId) return;
      
          const container = document.getElementById(targetId);
          if (!container) return;
      
          const step = getCarouselStep(container);
          const amount = btn.classList.contains('left') ? -step : step;
          container.scrollBy({ left: amount, behavior: 'smooth' });
        });
      });

    // Hide carousel arrows when content doesn't overflow (all cards visible)
    // -------------------------------------------------------------------------
    const updateCarouselArrows = () => {
        document.querySelectorAll('.carousel-wrapper').forEach((wrapper) => {
            const btns = wrapper.querySelectorAll('.nav-btn');
            const targetId = btns[0]?.dataset?.target;
            const container = targetId ? document.getElementById(targetId) : null;
            if (!container || !btns.length) return;

            const hasOverflow = container.scrollWidth > container.clientWidth;
            btns.forEach((b) => {
                b.style.display = hasOverflow ? '' : 'none';
            });
        });
    };

    updateCarouselArrows();
    window.addEventListener('resize', updateCarouselArrows);

    document.querySelectorAll('.carousel-wrapper').forEach((wrapper) => {
        const targetId = wrapper.querySelector('.nav-btn')?.dataset?.target;
        const container = targetId ? document.getElementById(targetId) : null;
        if (container && typeof ResizeObserver !== 'undefined') {
            new ResizeObserver(updateCarouselArrows).observe(container);
        }
    });

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
    // Scroll Animation Observer (Progressive Enhancement)
    // Uses IntersectionObserverAPI to trigger '.fade-in' animations.
    // -------------------------------------------------------------------------
    const cards = document.querySelectorAll('.card, .featured-story, .player-card, .metric-box, .project-card');

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

});