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
        const basePath = './';

        this.innerHTML = `
        <header class="site-header" id="mainHeader">
            <div class="main-nav-container container">
                <a href="${basePath}index.html" class="brand-logo">
                    <img src="${basePath}Images/NAU.png" alt="Northern Arizona University" class="header-logo">
                    <div class="brand-divider"></div>
                    <div class="brand-text">
                        <span class="dept">NAU Radiant Center for Remote Sensing</span>
                    </div>
                </a>

                <button type="button" class="mobile-toggle" aria-label="Open Menu" aria-expanded="false" aria-controls="site-nav-menu">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 12h18M3 6h18M3 18h18" />
                    </svg>
                </button>

                <nav class="nav-menu" id="site-nav-menu">
                    <div class="nav-item"><a href="${basePath}index.html" class="nav-link" data-path="index.html">Home</a></div>
                    <div class="nav-item"><a href="${basePath}Our_Team.html" class="nav-link" data-path="Our_Team.html">Our Team</a></div>
                    
                    <div class="nav-item"><a href="${basePath}Projects.html" class="nav-link" data-path="Projects.html">Projects</a></div>
                    
                    
                    <div class="nav-item"><a href="${basePath}Contact_Us.html" class="nav-link" data-path="Contact_Us.html">Contact Us</a></div>
                    <div class="nav-item nav-item-donate"><a href="https://securelb.imodules.com/s/1898/giving19/form.aspx?sid=1898&gid=2&pgid=418&bledit=1&dids=4256" target="_blank" rel="noopener" class="btn btn-sm btn-gold donate-nav-link">Donate</a></div>

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
        const mobileLayout = window.matchMedia('(max-width: 1024px)');

        if (!mobileBtn || !navMenu) return;

        let isMenuOpen = false;

        const syncMenuState = () => {
            const isMobileLayout = mobileLayout.matches;

            if (!isMobileLayout) {
                isMenuOpen = false;
                navMenu.hidden = false;
                navMenu.classList.remove('open');
                mobileBtn.setAttribute('aria-expanded', 'false');
                mobileBtn.setAttribute('aria-label', 'Open Menu');
                return;
            }

            navMenu.hidden = !isMenuOpen;
            navMenu.classList.toggle('open', isMenuOpen);
            mobileBtn.setAttribute('aria-expanded', String(isMenuOpen));
            mobileBtn.setAttribute('aria-label', isMenuOpen ? 'Close Menu' : 'Open Menu');
        };

        const closeMenu = () => {
            if (!mobileLayout.matches) return;
            isMenuOpen = false;
            syncMenuState();
        };

        const openMenu = () => {
            if (!mobileLayout.matches) return;
            isMenuOpen = true;
            syncMenuState();
        };

        // Start closed
        syncMenuState();

        mobileBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (!mobileLayout.matches) return;
            if (isMenuOpen) closeMenu();
            else openMenu();
        });

        // Close when selecting a link (mobile UX)
        navMenu.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (!link) return;
            closeMenu();
        });

        // Close on outside tap/click
        document.addEventListener('pointerdown', (e) => {
            if (!mobileLayout.matches || !isMenuOpen) return;
            if (navMenu.contains(e.target) || mobileBtn.contains(e.target)) return;
            closeMenu();
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key !== 'Escape') return;
            if (isMenuOpen) closeMenu();
        });

        if (typeof mobileLayout.addEventListener === 'function') {
            mobileLayout.addEventListener('change', syncMenuState);
        } else if (typeof mobileLayout.addListener === 'function') {
            mobileLayout.addListener(syncMenuState);
        }
    }
}

class SiteFooter extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        const basePath = './';

        this.innerHTML = `
        <footer class="site-footer">
            <div class="container">
                <div class="footer-grid">
                    <div class="footer-brand">
                        <img src="${basePath}Images/NAU.png" class="footer-logo" alt="NAU Logo"
                            onerror="this.style.display='none'">
                        <p style="color: rgba(255,255,255,0.7); max-width: 300px; margin-bottom: 25px;">The NAU Radiant Center for Remote Sensing advances remote sensing research, instrumentation, and real-world impact through interdisciplinary collaboration.</p>
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
                        <h4>Explore</h4>
                        <ul class="footer-links">
                            <li><a href="${basePath}index.html">Home</a></li>
                            <li><a href="${basePath}Projects.html">Projects</a></li>
                            <li><a href="${basePath}Our_Team.html">Our Team</a></li>
                            <li><a href="${basePath}Capabilities.html">Capabilities</a></li>
                        </ul>
                    </div>

                    <div class="footer-col">
                        <h4>Research</h4>
                        <ul class="footer-links">
                            <li><a href="${basePath}Projects.html">Featured Stories</a></li>
                            <li><a href="${basePath}Capabilities.html">Labs & Services</a></li>
                            <li><a href="https://directory.nau.edu/departments?id=11305" target="_blank" rel="noopener">NAU Directory</a></li>
                        </ul>
                    </div>

                    <div class="footer-col">
                        <h4>Connect</h4>
                        <ul class="footer-links">
                            <li><a href="${basePath}Contact_Us.html">Contact Us</a></li>
                            <li><a href="mailto:radiant@nau.edu">Email Radiant</a></li>
                            <li><a href="https://maps.google.com/?q=525%20S.%20Beaver%20St.,%204th%20Floor%20Flagstaff%20AZ" target="_blank" rel="noopener">Visit Campus</a></li>
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