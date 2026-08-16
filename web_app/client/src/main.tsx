import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// global.css first — it declares the cascade order, and a layer that appears
// before that declaration is pinned where it lands and the order silently
// stops applying. See styles/global.css.
import './styles/global.css'
import './styles/tokens.css'
import './styles/fonts.css'
import './styles/patterns.css'
import './styles.css'

import { App } from './App'

const root = document.getElementById('root')
if (!root) throw new Error('#root missing from index.html')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
