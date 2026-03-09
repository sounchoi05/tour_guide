package com.tourguide.aos

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.Menu
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import com.tourguide.aos.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding

    private val pages = mapOf(
        R.id.menu_itinerary to "/",
        R.id.menu_audio to "/audio",
        R.id.menu_expense to "/expense"
    )

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)

        val webSettings = binding.webView.settings
        webSettings.javaScriptEnabled = true
        webSettings.domStorageEnabled = true
        webSettings.allowFileAccess = false
        webSettings.loadsImagesAutomatically = true

        binding.webView.webChromeClient = WebChromeClient()
        binding.webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                return false
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                binding.swipeRefresh.isRefreshing = false
            }

            @Deprecated("Deprecated in Java")
            override fun onReceivedError(
                view: WebView?,
                errorCode: Int,
                description: String?,
                failingUrl: String?
            ) {
                binding.swipeRefresh.isRefreshing = false
                Toast.makeText(
                    this@MainActivity,
                    getString(R.string.loading_failed, description ?: "unknown"),
                    Toast.LENGTH_SHORT
                ).show()
            }
        }

        binding.swipeRefresh.setOnRefreshListener {
            binding.webView.reload()
        }

        binding.fabHome.setOnClickListener {
            openPath("/")
        }

        openPath("/")

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (binding.webView.canGoBack()) binding.webView.goBack() else finish()
            }
        })
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: android.view.MenuItem): Boolean {
        pages[item.itemId]?.let {
            openPath(it)
            return true
        }
        return super.onOptionsItemSelected(item)
    }

    private fun openPath(path: String) {
        val target = BuildConfig.BASE_URL.trimEnd('/') + path
        binding.webView.loadUrl(target)
    }
}
