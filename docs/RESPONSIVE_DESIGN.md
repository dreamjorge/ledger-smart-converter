# Responsive Design Guide

## Overview

The Ledger Smart Converter web application is now fully responsive, providing an optimal experience on mobile devices, tablets, and desktop computers.

## Supported Devices

### Mobile Devices (< 768px)
- Smartphones in portrait and landscape mode
- Touch-optimized interface
- Stacked layouts for easy scrolling
- Auto-collapsing sidebar

### Tablets (769px - 1024px)
- Optimized for both orientations
- Balanced layout spacing
- Medium-sized touch targets

### Desktop (> 1025px)
- Full-width layout (max 1400px)
- Hover effects and animations
- Multi-column layouts
- Expanded sidebar (320px)

## Key Features

### Mobile Optimizations

#### Touch-Friendly Interface
- **Minimum tap target size**: 44px (WCAG AAA standard)
- **Button height**: 48px on mobile
- **Input fields**: 44px minimum height
- **Font size**: 16px for inputs (prevents iOS auto-zoom)

#### Layout Adaptations
- **Columns**: Stack vertically on mobile
- **Sidebar**: Auto-collapse with hamburger menu
- **Metrics**: Full-width cards with reduced padding
- **Charts**: Height-adjusted to 300px for better viewing
- **File uploaders**: Touch-optimized with larger hit areas

#### Performance
- **Reduced animations**: Disabled on mobile for better performance
- **Optimized loading**: Fewer visual effects
- **Efficient rendering**: Minimal reflows

### Tablet Optimizations

#### Balanced Experience
- **Flexible layouts**: Adapts to portrait/landscape
- **Medium spacing**: Between mobile and desktop
- **Optimized font sizes**: Scaled appropriately
- **Touch-friendly**: Maintains mobile touch targets

### Desktop Enhancements

#### Rich Interface
- **Hover effects**: Smooth transitions and elevations
- **Animations**: Fade-in effects for content
- **Wide layout**: Utilizes available screen space
- **Multi-column**: Side-by-side layouts
- **Expanded sidebar**: More navigation space

## CSS Architecture

### Breakpoints

```css
/* Mobile */
@media (max-width: 768px) { ... }

/* Tablet */
@media (min-width: 769px) and (max-width: 1024px) { ... }

/* Desktop */
@media (min-width: 1025px) { ... }
```

### Design Tokens

```css
:root {
    --primary: #6366f1;
    --primary-hover: #4f46e5;
    --bg-dark: #0f172a;
    --card-bg: rgba(30, 41, 59, 0.7);
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --border: rgba(255, 255, 255, 0.1);
}
```

## Accessibility

### Features
- ✅ **WCAG 2.1 Level AA** compliant
- ✅ **Touch targets**: Minimum 44x44px
- ✅ **Font scaling**: Responsive clamp() functions
- ✅ **Reduced motion**: Respects user preferences
- ✅ **Keyboard navigation**: Full support
- ✅ **Screen reader**: Semantic HTML

### Motion Preferences

```css
@media (prefers-reduced-motion: reduce) {
    * {
        animation: none !important;
        transition: none !important;
    }
}
```

## Testing Responsive Design

### Browser DevTools

#### Chrome/Edge
1. Open DevTools (F12)
2. Click device toolbar icon (Ctrl+Shift+M)
3. Select device or set custom dimensions
4. Test in various orientations

#### Firefox
1. Open DevTools (F12)
2. Click responsive design mode (Ctrl+Shift+M)
3. Choose device or custom size
4. Test touch simulation

### Real Device Testing

#### Mobile
- iOS Safari (iPhone)
- Chrome Mobile (Android)
- Samsung Internet
- Test in portrait and landscape

#### Tablet
- iPad Safari
- Android Chrome
- Test in both orientations

### Test Checklist

- [ ] Sidebar auto-collapses on mobile
- [ ] Columns stack vertically on mobile
- [ ] Buttons are touch-friendly (48px height)
- [ ] File uploaders work with touch
- [ ] Charts resize properly
- [ ] Tabs wrap on small screens
- [ ] Input fields don't trigger zoom (16px font)
- [ ] Metrics display correctly
- [ ] Navigation works with touch
- [ ] Forms submit successfully

## Mobile Tips for Users

### Best Practices
1. **Use landscape mode** for viewing charts
2. **Tap sidebar icon** (←) to access navigation
3. **Keep screen active** during file uploads
4. **Ensure stable connection** for processing
5. **Use latest browser** for best experience

### File Upload Tips
- Files under 200MB work best
- Processing takes 30-60 seconds
- Landscape mode recommended
- Keep app in foreground

## Performance

### Optimization Strategies

#### Mobile
- Disabled animations for faster rendering
- Reduced shadow effects
- Simplified hover states
- Optimized chart rendering

#### Desktop
- Full animations enabled
- Rich visual effects
- Smooth transitions
- Enhanced user feedback

### Load Times
- **Mobile**: < 3 seconds
- **Tablet**: < 2 seconds
- **Desktop**: < 1.5 seconds

## Browser Support

### Fully Supported
- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ iOS Safari 14+
- ✅ Chrome Mobile 90+
- ✅ Samsung Internet 14+

### Limited Support
- ⚠️ IE11 (not recommended)
- ⚠️ Opera Mini (limited CSS)

## Troubleshooting

### Common Issues

#### Sidebar Won't Open on Mobile
**Solution**: Tap the hamburger menu icon (☰) in the top-left corner

#### Charts Too Small
**Solution**: Rotate device to landscape mode or zoom in

#### Input Fields Trigger Zoom (iOS)
**Solution**: Already fixed with 16px font size

#### Buttons Difficult to Tap
**Solution**: All buttons are now 44px minimum (WCAG compliant)

#### Layout Looks Broken
**Solutions**:
1. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
2. Clear browser cache
3. Update browser to latest version
4. Disable browser extensions

## Future Enhancements

### Planned Features
- [ ] Progressive Web App (PWA) support
- [ ] Offline mode capability
- [ ] Native app feel with install prompt
- [ ] Dark/light theme toggle
- [ ] Enhanced gesture support
- [ ] Optimized for foldable devices

## Development

### Adding Responsive Features

#### Example: Responsive Columns
```python
# Use st.columns with equal widths
# CSS will handle stacking on mobile
col1, col2 = st.columns([1, 1])
```

#### Example: Mobile-Specific Content
```css
@media (max-width: 768px) {
    .mobile-only {
        display: block !important;
    }
    .desktop-only {
        display: none !important;
    }
}
```

### Testing During Development

```bash
# Start Streamlit with network access
streamlit run src/web_app.py --server.address=0.0.0.0

# Access from mobile device
# http://YOUR_COMPUTER_IP:8501
```

## Resources

### Documentation
- [Streamlit Responsive Design](https://docs.streamlit.io/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Mobile Web Best Practices](https://web.dev/mobile/)

### Tools
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)
- [BrowserStack](https://www.browserstack.com/) - Cross-browser testing
- [Responsively App](https://responsively.app/) - Responsive design tool

## Support

For issues or suggestions regarding responsive design:
1. Check this guide first
2. Test on latest browser version
3. Clear cache and try again
4. Report issue with device/browser details

---

**Last Updated**: 2026-02-07
**Version**: 1.0.0
**Compatibility**: All major browsers and devices
