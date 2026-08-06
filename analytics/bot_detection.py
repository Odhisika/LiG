from django.db.models import Q


BOT_TOKENS = [
    # Search engine crawlers
    'googlebot', 'bingbot', 'bingpreview', 'slurp', 'duckduckbot',
    'baiduspider', 'yandex', 'yandexbot', 'sogou', 'exabot', 'applebot',
    'ia_archiver', 'archive.org', 'nutch', 'mediapartners', 'adsbot',
    'adscanner', 'googleother', 'google-inspectiontool', 'bingpagerender',
    'petalbot',
    # Social media / link preview bots
    'facebookexternalhit', 'facebot', 'twitterbot', 'linkedinbot',
    'whatsapp', 'telegrambot', 'slackbot', 'discordbot', 'skypeuripreview',
    'pinterest', 'redditbot', 'instagram', 'tiktok', 'snapchat', 'quora',
    'embedly', 'outbrain', 'rogerbot',
    # SEO / analytics / uptime monitoring
    'mj12bot', 'ahrefsbot', 'semrushbot', 'dotbot', 'uptimerobot',
    'uptime', 'pingdom', 'site24x7', 'paessler', 'monitoring', 'monitor',
    'screaming', 'semalt', 'checker', 'verifier', 'fetcher', 'feedfetcher',
    'feedburner', 'appengine',
    # Headless / automation / scraping clients
    'headless', 'phantomjs', 'puppeteer', 'playwright', 'selenium',
    'scrapy', 'splunk', 'nimbostratus',
    # CLI / programmatic HTTP clients
    'curl', 'wget', 'libwww', 'httpclient', 'apache-httpclient',
    'python-requests', 'python-urllib', 'go-http-client', 'java',
    'python', 'node', 'axios', 'okhttp', 'postman', 'httpie',
    # Generic markers
    'bot', 'crawler', 'crawl', 'spider', 'preview', 'scan',
]


def is_bot(user_agent):
    """Return True if the User-Agent looks like a bot/crawler/script.

    Missing or empty User-Agents are treated as bots because real browsers
    always send one.
    """
    if not user_agent:
        return True
    ua = user_agent.lower()
    return any(token in ua for token in BOT_TOKENS)


def bot_q(field='user_agent'):
    """Return a Q usable with .exclude() to drop bot/missing User-Agents.

    ``field`` is the query path to the User-Agent column, e.g.
    ``'user_agent'`` for Visitor or ``'visitor__user_agent'`` for PageView.
    """
    q = Q(**{f'{field}__isnull': True}) | Q(**{f'{field}': ''})
    for token in BOT_TOKENS:
        q |= Q(**{f'{field}__icontains': token})
    return q
