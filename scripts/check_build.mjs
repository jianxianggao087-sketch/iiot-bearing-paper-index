import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';

const DIST = 'dist';
const errors = [];
const indexHtml = join(DIST, 'index.html');
if (!existsSync(indexHtml)) errors.push('dist/index.html 不存在');

const html = existsSync(indexHtml) ? readFileSync(indexHtml, 'utf8') : '';
const cardCount = (html.match(/class="paper-card"/g) || []).length;
if (cardCount < 1 && process.env.ALLOW_EMPTY !== '1') errors.push('index.html 中没有任何论文卡片');
if (!/site-header/.test(html)) errors.push('缺少站点头部');
if (!existsSync(join(DIST, 'about', 'index.html'))) errors.push('dist/about/index.html 不存在');

const walk = (dir) => readdirSync(dir).flatMap((name) => {
  const full = join(dir, name);
  return statSync(full).isDirectory() ? walk(full) : [full];
});
if (existsSync(DIST)) {
  for (const file of walk(DIST)) {
    if (['.db', '.sqlite'].includes(extname(file))) errors.push(`构建产物包含数据库文件: ${file}`);
  }
}

if (errors.length) {
  console.error('构建校验失败:\n- ' + errors.join('\n- '));
  process.exit(1);
}
console.log(`构建校验通过：${cardCount} 张卡片`);
