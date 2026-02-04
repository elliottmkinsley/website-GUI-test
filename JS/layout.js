/**
 * Layout Components
 * --------------------------------------
 * Defines custom web components <site-header> and <site-footer> 
 * to ensure consistency across all pages without server-side includes.
 */

class SiteHeader extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        // DYNAMIC PATH LOGIC
       
        const isInSubfolder = window.location.pathname.includes('/About_Equipment/');
        const basePath = isInSubfolder ? '../' : './';

        this.innerHTML = `
        <header class="site-header" id="mainHeader">
            <div class="main-nav-container container">
                <a href="${basePath}index.html" class="brand-logo">
                    <img src="${basePath}Images/NAU.png" alt="Northern Arizona University" class="header-logo">
                    <div class="brand-divider"></div>
                    <div class="brand-text">
                        <span class="dept">Microelectronics at NAU</span>
                    </div>
                </a>

                <button class="mobile-toggle" aria-label="Open Menu">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 12h18M3 6h18M3 18h18" />
                    </svg>
                </button>

                <nav class="nav-menu">
                    <div class="nav-item"><a href="${basePath}index.html" class="nav-link" data-path="index.html">Home</a></div>
                    <div class="nav-item"><a href="${basePath}Academics.html" class="nav-link">Featured Degrees</a></div>
                    
                    <div class="nav-item"><a href="${basePath}Equipment.html" class="nav-link" data-path="Equipment.html">Equipment</a></div>
                    
                    <div class="nav-item"><a href="${basePath}About_Us.html" class="nav-link">About Us</a></div>
                    
                    <div class="nav-item"><a href="${basePath}Contact_Us.html" class="nav-link" data-path="Contact_Us.html">Contact Us</a></div>
                    
                    <div class="nav-item"><a href="https://outlook.office.com/book/iMPaCTNanoLab@bookings.nau.edu/?ismsaljsauthenabled" target="_blank" class="btn btn-sm btn-gold">Reserve Equipment</a></div>
                </nav>
            </div>
        </header>
        `;

        this.highlightActiveLink();
        this.initMobileMenu();
    }

    highlightActiveLink() {
        const currentPath = window.location.pathname.split('/').pop() || 'index.html';
        const links = this.querySelectorAll('.nav-link');

        links.forEach(link => {
            if (link.dataset.path === currentPath) {
                link.classList.add('active');
            }
        });
    }

    initMobileMenu() {
        const mobileBtn = this.querySelector('.mobile-toggle');
        const navMenu = this.querySelector('.nav-menu');

        if (mobileBtn) {
            mobileBtn.addEventListener('click', () => {
                const isHidden = window.getComputedStyle(navMenu).display === 'none';
                if (isHidden) {
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
                    if (window.innerWidth > 1024) navMenu.style.display = '';
                }
            });
        }
    }
}

class SiteFooter extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        // Re-use dynamic path logic for the footer images/links
        const isInSubfolder = window.location.pathname.includes('/About_Equipment/');
        const basePath = isInSubfolder ? '../' : './';

        this.innerHTML = `
        <footer class="site-footer">
            <div class="container">
                <div class="footer-grid">
                    <div class="footer-brand">
                        <img src="${basePath}Images/NAU.png" class="footer-logo" alt="NAU Logo"
                            onerror="this.style.display='none'">
                        <p style="color: rgba(255,255,255,0.7); max-width: 300px; margin-bottom: 25px;">The Microelectronics
                            Processing,
                            Characterization, and Testing Lab is dedicated to advancing semiconductor education and
                            research.</p>
                        <div class="social-row">
                             <a href="https://twitter.com/NAU" target="_blank" class="social-icon" aria-label="X (Twitter)">
                                <svg viewBox="0 0 24 24">
                                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"></path>
                                </svg>
                            </a>
                            <a href="https://www.facebook.com/NAU/" target="_blank" class="social-icon" aria-label="Facebook">
                                <svg viewBox="0 0 24 24"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path></svg>
                            </a>
                            <a href="https://www.instagram.com/nauflagstaff/" target="_blank" class="social-icon" aria-label="Instagram">
                                <svg viewBox="0 0 24 24">
                                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                                    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                                    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
                                </svg>
                            </a>
                            <a href="https://www.linkedin.com/school/northern-arizona-university/" target="_blank" class="social-icon" aria-label="LinkedIn">
                                <svg viewBox="0 0 24 24">
                                    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path>
                                    <rect x="2" y="9" width="4" height="12"></rect>
                                    <circle cx="4" cy="4" r="2"></circle>
                                </svg>
                            </a>
                        </div>
                    </div>

                    <div class="footer-col">
                        <h4>User Portal</h4>
                        <ul class="footer-links">
                            <li><a href="${basePath}Booking1.html">Book Equipment</a></li>
                            <li><a href="#">Report an Issue</a></li>
                            <li><a href="#">Safety Training</a></li>
                            <li><a href="#">SDS Database</a></li>
                            <li><a href="#">Lab Policies</a></li>
                        </ul>
                    </div>

                    <div class="footer-col">
                        <h4>Academics</h4>
                        <ul class="footer-links">
                            <li><a href="#">Undergraduate Courses</a></li>
                            <li><a href="#">Graduate Research</a></li>
                            <li><a href="#">Certificate Programs</a></li>
                            <li><a href="#">Student Projects</a></li>
                        </ul>
                    </div>

                    <div class="footer-col">
                        <h4>Connect</h4>
                        <ul class="footer-links">
                            <li><a href="${basePath}Contact_Us.html">Contact Us</a></li>
                            <li><a href="#">Partner With Us</a></li>
                            <li><a href="#">Alumni Network</a></li>
                            <li><a href="#">Support NAU Nano</a></li>
                        </ul>
                    </div>
                </div>
            </div>

            <div class="footer-bottom">
                <div class="container footer-bottom-flex">
                    <p>&copy; 2026 Northern Arizona University. All Rights Reserved.</p>
                    <div class="footer-links-flex">
                        <a href="#" class="footer-link-mute">Nondiscrimination</a>
                        <a href="#" class="footer-link-mute">Accessibility</a>
                        <a href="#" class="footer-link-mute">Privacy</a>
                    </div>
                </div>
            </div>
        </footer>
        `;
    }
}

// Register Components
customElements.define('site-header', SiteHeader);
customElements.define('site-footer', SiteFooter);