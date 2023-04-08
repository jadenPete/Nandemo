const path = require("path");

module.exports = {
	entry: "./static/ts/index.ts",
	externals: {
		bootstrap: "bootstrap",
	},

	output: {
	filename: "index.js",
		path: path.resolve(__dirname, "static", "js"),
	},

	module: {
		rules: [
			{
				test: /\.tsx?$/,
				loader: "ts-loader"
			}
		]
	},

	resolve: {
		extensions: [".js", ".ts", ".tsx"]
	}
};
