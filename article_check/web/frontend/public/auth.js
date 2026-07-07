(() => {
  const defaultConfig = {
    enabled: !['localhost', '127.0.0.1'].includes(window.location.hostname),
    host: 'http://124.71.226.114:8444',
    storagePrefix: 'article_check_platform_',
    debug: false,
  };

  const runtimeConfig = window.__ARTICLE_CHECK_PLATFORM_AUTH__ || {};
  const config = { ...defaultConfig, ...runtimeConfig };

  const log = (...args) => {
    if (config.debug) {
      console.log('[platform-auth]', ...args);
    }
  };

  if (!config.enabled) {
    log('平台认证脚本已加载，但当前环境未启用认证。');
    return;
  }

  const API = {
    OAUTH: {
      AUTH: `${config.host}/api/oauth/auth`,
      TOKEN: `${config.host}/api/oauth/token`,
      REFRESH: `${config.host}/api/oauth/refresh`,
      INTROSPECT: `${config.host}/api/oauth/introspect`,
    },
  };

  const accessTokenKey = `${config.storagePrefix}access_token`;
  const refreshTokenKey = `${config.storagePrefix}refresh_token`;
  const idTokenKey = `${config.storagePrefix}id_token`;
  const expiresInKey = `${config.storagePrefix}expires_in`;

  auth().then((ok) => {
    if (!ok) {
      alert('平台认证失败，请联系管理员检查 OAuth 配置。');
    }
  });

  async function auth() {
    const paramsString = window.location.search;
    const pathParams = new URLSearchParams(paramsString);
    const code = pathParams.get('code');
    const state = pathParams.get('state');

    if (!code) {
      const accessToken = localStorage.getItem(accessTokenKey);
      if (!accessToken) {
        return redirect();
      }

      const expiresIn = localStorage.getItem(expiresInKey);
      if (expiresIn && Date.now() > Number(expiresIn)) {
        return refreshToken();
      }
      return introspectToken();
    }

    log('oauth callback', { code, state });
    const result = await getToken(code, state);
    window.history.replaceState({}, document.title, window.location.pathname);
    return result;
  }

  async function redirect() {
    const redirectUri = window.location.origin + window.location.pathname;
    const url = `${API.OAUTH.AUTH}?redirectUri=${encodeURIComponent(redirectUri)}`;

    try {
      const response = await fetch(url, { method: 'GET', redirect: 'follow' });
      const result = await response.json();
      window.location.href = result.auth_url;
      return true;
    } catch (error) {
      console.error('redirect auth error:', error);
      return false;
    }
  }

  async function getToken(code) {
    const raw = JSON.stringify({
      code,
      redirect_uri: window.location.origin + window.location.pathname,
    });

    try {
      const response = await fetch(API.OAUTH.TOKEN, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: raw,
        redirect: 'follow',
      });
      const result = await response.json();
      localStorage.setItem(accessTokenKey, result.access_token);
      localStorage.setItem(refreshTokenKey, result.refresh_token);
      localStorage.setItem(idTokenKey, result.id_token);
      localStorage.setItem(expiresInKey, Date.now() + (result.expires_in * 1000));
      return true;
    } catch (error) {
      console.error('get token error:', error);
      return false;
    }
  }

  async function refreshToken() {
    try {
      const response = await fetch(API.OAUTH.REFRESH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          refresh_token: localStorage.getItem(refreshTokenKey),
        }),
        redirect: 'follow',
      });
      const result = await response.json();
      localStorage.setItem(accessTokenKey, result.access_token);
      localStorage.setItem(refreshTokenKey, result.refresh_token);
      localStorage.setItem(idTokenKey, result.id_token);
      localStorage.setItem(expiresInKey, Date.now() + (result.expires_in * 1000));
      return true;
    } catch (error) {
      console.error('refresh token error:', error);
      return false;
    }
  }

  async function introspectToken() {
    try {
      const response = await fetch(API.OAUTH.INTROSPECT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: localStorage.getItem(accessTokenKey),
        }),
        redirect: 'follow',
      });
      const result = await response.json();
      if (result.active !== true) {
        return redirect();
      }
      return true;
    } catch (error) {
      console.error('introspect token error:', error);
      return false;
    }
  }
})();
