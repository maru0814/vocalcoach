/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 本番Dockerを小さくするための standalone 出力
  output: "standalone",
};

module.exports = nextConfig;
