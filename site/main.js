(() => {
  'use strict';
  const en = {
    skipLink:'Skip to content',
    navStory:'The origin',navProject:'The project',navHow:'How it works',navFuture:'The future',navDownload:'Download ↗',
    heroEyebrow:'OPEN-SOURCE PROJECT · EXPERIMENTAL BETA',
    heroTitle:'Hardware can fail.<br><em>The console lives on.</em>',
    heroDesc:'Giving the original Xbox a second life on compatible PC hardware. A dedicated console experience born from the wish to save a gaming system that seemed lost.',
    heroButton:'Explore the beta',heroNote:'Built for the community. Always evolving.',scrollCue:'SCROLL TO EXPLORE',
    signal1:'PRESERVATION',signal2:'REUSED HARDWARE',signal3:'CONTROLLER-FIRST',signal4:'OPEN SOURCE',
    storyTitle:'It started with<br><em>a flood-damaged Xbox.</em>',
    storyLead:'A damaged motherboard. An unused laptop. And one question: what if that Xbox could come back to life without losing its identity?',
    storyP1:'The original Xbox has always been special to me. Its PC-like architecture inspired an idea: replace failing proprietary hardware with ordinary components, while keeping the console experience.',
    storyP2:'The idea grew. What began as a rescue for a single machine became X-Revive: an initiative focused on preservation, low-level research and giving PC hardware new purpose for retro gaming.',
    storyAuthor:'Creator of X-Revive',
    quote:'It was never just about getting a game to run. It was about bringing my console back — and learning how to help others do the same.',
    projectTitle:'Not just launching an emulator.<br><em>Powering on a console.</em>',
    projectLead:'X-Revive turns compatible PCs into a dedicated original Xbox environment. Minimal Linux behind the scenes; a console experience in front of the TV.',
    feature1Title:'Power on. Enter Xbox.',feature1Text:'UEFI boot, a dedicated environment and a dashboard. No desktop session needed to manually start Xemu.',
    feature2Title:'Controller-first',feature2Text:'Installation and operation designed to work with a compatible controller or keyboard.',
    feature3Title:'FATX storage',feature3Text:'Xbox games and apps in a console environment, with a standalone installation on a dedicated HDD/SSD.',
    feature4Title:'Included drivers',feature4Text:'Linux system with Mesa and NVIDIA 550 in this beta; actual compatibility depends on CPU, GPU and emulation.',
    feature5Title:'Maintenance and recovery',feature5Text:'Boot shortcuts for maintenance, diagnostics and support using the USB medium.',
    stepsTitle:'Download. Flash.<br><em>Install. Play.</em>',
    stepsLead:'The public beta offers a guided install without compiling source code. Read the warnings before choosing a disk.',
    step1Title:'Download the image',step1Text:'Get the released beta image and verify its SHA256 checksum.',
    step2Title:'Prepare a USB drive',step2Text:'Flash the IMG to a USB drive of at least 16 GB, then add your legally obtained Xbox files.',
    step3Title:'Install to a test drive',step3Text:'Select a dedicated HDD/SSD. A clean installation erases the ENTIRE selected disk.',
    step4Title:'Power on your console',step4Text:'Once installed, boot straight into the Xbox environment from the disk — no USB stick needed.',
    safetyTitle:'Protect your existing data.',
    safetyText:'Choose the mode: installing ERASES the target HDD/SSD. Protected LIVE keeps changes in RAM. Boot preparation or repair requires space outside FATX and two confirmations; automatic F resizing is not included.',
    preserveTitle:'Preserve what<br><em>matters.</em>',
    preserveP1:'The original motivation is still at the heart of the project: reusing an original Xbox HDD, including its FATX partitions, games and identity. The beta includes protected USB/RAM LIVE and UEFI boot preparation or repair where space exists outside Xbox volumes.',
    preserveP2:'When F fills the disk, migration remains experimental. Original disks and physical Xbox hardware require validation for each scenario, verified backups and integrity checks.',
    preserveLink:'Explore HDD preservation research ↗',
    visionTitle:'A second life for Xbox.<br><em>A world of possibilities.</em>',
    visionLead:'X-Revive is dedicated to the original Xbox. In the future, separate projects may follow the same philosophy: one SSD per console, on compatible hardware, with a unique experience from power-on.',
    visionNow:'NOW · X-REVIVE',visionCard1Title:'Original Xbox',visionCard1Text:'Improve the beta, test additional hardware, refine setup, preserve user data and expand compatibility.',
    visionNext:'FUTURE VISION · SEPARATE PROJECTS',visionCard2Title:'Other consoles, new cartridges',visionCard2Text:'Ideas such as PS2-Renew and Wii/GC-Boot are independent future initiatives, not available features of this beta.',
    visionFootnote:'Long-term research includes open firmware and alternative ways to execute XBE software and translate hardware behavior. The current version does not promise native XBE execution or 100% game compatibility.',
    downloadLabel:'PUBLIC RELEASE · EXPERIMENTAL',downloadTitle:'Your next Xbox<br><em>starts here.</em>',
    downloadDesc:'The public v0.1.0-beta.5-live.6 image targets x86-64 UEFI PCs. BIOS, MCPX, personal EEPROM, games and proprietary assets are not included. Supply your BIOS and MCPX; EEPROM is optional and Xemu generates one when absent.',
    downloadCTA:'Download IMG · beta.5-live.6',guideCTA:'Installation guide ↗',downloadMeta:'USB ≥ 16 GB · LIVE or installation · check the selected mode',allReleases:'All releases ↗',
    communityTitle:'Not just a project.<br><em>A community effort.</em>',
    communityText:'X-Revive welcomes research, testing, compatibility reports and contributions. If you know Xbox, Linux, emulation or reverse engineering — or have different hardware to test — there are ways to help.',
    communityIssue:'Report an issue ↗',communityContrib:'Contribute ↗',communityDocs:'Full documentation ↗',
    footerMission:'Preserve the past. Rebuild the hardware. Keep Xbox alive.',footerDisclaimer:'Independent project. Not affiliated with Microsoft or Xbox.'
  };
  const menuButton = document.getElementById('menu-toggle');
  const navLinks = document.getElementById('nav-links');
  const setMenu = (open, restoreFocus = false) => {
    const english = document.documentElement.lang === 'en';
    menuButton?.setAttribute('aria-expanded', String(open));
    menuButton?.setAttribute('aria-label', english
      ? (open ? 'Close menu' : 'Open menu')
      : (open ? 'Fechar menu' : 'Abrir menu'));
    navLinks?.classList.toggle('open', open);
    if (restoreFocus) menuButton?.focus();
  };
  menuButton?.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    setMenu(open);
  });
  navLinks?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
      setMenu(false, true);
    }
  });
  window.matchMedia('(min-width: 761px)').addEventListener('change', event => {
    if (event.matches) setMenu(false);
  });
  const originals = {};
  document.querySelectorAll('[data-i18n], [data-i18n-html]').forEach(el => {
    const key = el.dataset.i18n || el.dataset.i18nHtml;
    originals[key] = el.dataset.i18nHtml ? el.innerHTML : el.textContent;
  });
  const languageToggle = document.getElementById('language-toggle');
  const setLanguage = lang => {
    document.documentElement.lang = lang === 'en' ? 'en' : 'pt-BR';
    document.querySelectorAll('[data-i18n], [data-i18n-html]').forEach(el => {
      const isHtml = Boolean(el.dataset.i18nHtml);
      const key = el.dataset.i18n || el.dataset.i18nHtml;
      const value = lang === 'en' && en[key] ? en[key] : originals[key];
      if (isHtml) el.innerHTML = value;
      else el.textContent = value;
    });
    if (languageToggle) {
      languageToggle.innerHTML = lang === 'en' ? 'PT <span aria-hidden="true">↗</span>' : 'EN <span aria-hidden="true">↗</span>';
      languageToggle.setAttribute('aria-label', lang === 'en' ? 'Mudar o site para português' : 'Switch site language to English');
      languageToggle.title = lang === 'en' ? 'Português' : 'English';
    }
    setMenu(menuButton?.getAttribute('aria-expanded') === 'true');
    document.title = lang === 'en' ? 'X-Revive — Hardware can fail. The console lives on.' : 'X-Revive — O hardware pode morrer. O console não.';
    try { localStorage.setItem('xrevive-lang', lang); } catch (_) {}
  };
  let current = 'pt';
  try { current = localStorage.getItem('xrevive-lang') === 'en' ? 'en' : 'pt'; } catch (_) {}
  setLanguage(current);
  languageToggle?.addEventListener('click', () => { current = current === 'pt' ? 'en' : 'pt'; setLanguage(current); });
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); } });
    }, { threshold: .08, rootMargin: '0px 0px 80px 0px' });
    document.querySelectorAll('.reveal').forEach(el => {
      el.classList.add('reveal-ready');
      observer.observe(el);
    });
  } else { document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible')); }
})();
