/* =========================================================
   汽车租赁智能管理系统 - 全局脚本
   包含：全局消息提示、验证码倒计时、收藏切换、价格预览等
   ========================================================= */

(function ($) {
  'use strict';

  /* ---------- 全局消息提示（页面顶端居中弹窗，3 秒自动消失） ---------- */
  var $toast = $('<div class="toast-global"></div>').appendTo('body');
  window.showToast = function (message, type) {
    type = type || 'success';
    $toast.removeClass('toast-success toast-error').addClass('toast-' + type)
      .text(message).fadeIn(180);
    clearTimeout($toast.data('timer'));
    $toast.data('timer', setTimeout(function () {
      $toast.fadeOut(250);
    }, 3000));
  };

  // 页面加载时读取 Django messages 渲染全局提示
  $(function () {
    $('.django-msg').each(function () {
      var type = $(this).data('type') || 'success';
      var text = $(this).data('text') || '';
      if (text) {
        // 将 Django message level 映射为 success/error
        var cls = 'success';
        if (type === 'error' || type === 'warning') cls = 'error';
        window.showToast(text, cls);
      }
    });
  });

  /* ---------- 邮箱验证码发送（60 秒倒计时） ---------- */
  $(document).on('click', '.btn-send-code', function () {
    var $btn = $(this);
    var email = $btn.data('target');
    if (!email) {
      var $input = $('input[name="email"]');
      if ($input.length && $input.val()) email = $input.val();
    }
    if (!email) {
      window.showToast('请先填写邮箱', 'error');
      return;
    }
    $btn.prop('disabled', true);
    $.ajax({
      url: '/send-code/',
      method: 'POST',
      data: {
        email: email,
        csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
      },
      dataType: 'json',
      success: function (res) {
        window.showToast(res.message, res.success ? 'success' : 'error');
        if (res.success) startCountdown($btn, 60);
        else $btn.prop('disabled', false);
      },
      error: function (xhr) {
        var msg = '验证码发送失败';
        if (xhr.responseJSON && xhr.responseJSON.message) msg = xhr.responseJSON.message;
        window.showToast(msg, 'error');
        $btn.prop('disabled', false);
      }
    });
  });

  function startCountdown($btn, seconds) {
    var left = seconds;
    var original = $btn.data('original-text') || $btn.text();
    $btn.data('original-text', original);
    $btn.text(left + 's 后重发');
    var timer = setInterval(function () {
      left -= 1;
      if (left <= 0) {
        clearInterval(timer);
        $btn.prop('disabled', false).text(original);
      } else {
        $btn.text(left + 's 后重发');
      }
    }, 1000);
  }

  /* ---------- 收藏/取消收藏 ---------- */
  $(document).on('click', '.fav-toggle', function () {
    var $btn = $(this);
    var vehicleId = $btn.data('vehicle-id');
    $.ajax({
      url: '/favorites/toggle/',
      method: 'POST',
      data: {
        vehicle_id: vehicleId,
        csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
      },
      dataType: 'json',
      success: function (res) {
        if (res.success) {
          window.showToast(res.message, 'success');
          // 切换背景类 + 心形图标（bi-heart 空心 ↔ bi-heart-fill 实心，同字号同基线）
          $btn.removeClass('btn-accent btn-light-soft btn-outline-primary')
            .addClass(res.is_favorited ? 'btn-accent' : 'btn-light-soft');
          $btn.find('.fav-heart')
            .removeClass('bi-heart bi-heart-fill')
            .addClass(res.is_favorited ? 'bi-heart-fill' : 'bi-heart');
          // 收藏数量实时更新：详情页按钮与数量是兄弟节点，卡片页再退回容器查找
          var $count = $btn.siblings('.fav-count');
          if (!$count.length) {
            $count = $btn.closest('.card, .vehicle-card, .d-flex').find('.fav-count');
          }
          if ($count.length) $count.text(res.favorite_count);
        } else {
          window.showToast(res.message, 'error');
        }
      },
      error: function () {
        window.showToast('操作失败，请稍后重试', 'error');
      }
    });
  });

  /* ---------- 通用确认弹窗 ---------- */
  window.confirmAction = function (message, formId) {
    if (window.confirm(message || '确定执行该操作吗？')) {
      $('#' + formId).submit();
    }
  };

})(jQuery);
