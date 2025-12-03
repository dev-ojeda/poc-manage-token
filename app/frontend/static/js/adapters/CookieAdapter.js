export class CookieAdapter {
    /**
     * Establece una cookie.
     * @param {string} key 
     * @param {string} value 
     * @param {object} options - { days, path, secure, sameSite }
     */
    setItem(key, value, options = {}) {
        const {
            days = 7,
            path = '/',
            secure = true,
            sameSite = 'Strict'
        } = options;

        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        const encoded = encodeURIComponent(value);

        document.cookie = `${key}=${encoded}; Expires=${expires}; Path=${path}; SameSite=${sameSite};${secure ? ' Secure;' : ''}`;
    }

    /**
     * Obtiene una cookie por clave.
     * @param {string} key 
     * @returns {string|null}
     */
    getItem(key) {
        return document.cookie
            .split('; ')
            .find(row => row.startsWith(`${key}=`))
            ?.split('=')[1] ?? null;
    }

    /**
     * Elimina una cookie.
     * @param {string} key 
     * @param {object} options - { path }
     */
    removeItem(key, options = {}) {
        const { path = '/' } = options;
        document.cookie = `${key}=; Max-Age=0; Path=${path};`;
    }

    /**
     * Limpia todas las cookies visibles desde el path actual.
     */
    clear() {
        document.cookie.split(';').forEach(cookie => {
            const key = cookie.split('=')[0].trim();
            this.removeItem(key);
        });
    }

    /**
     * Cuenta cuántas cookies están disponibles.
     * @returns {number}
     */
    countItem() {
        return document.cookie.split(';').filter(Boolean).length;
    }
}
