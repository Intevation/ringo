<%inherit file="/main.mako" />
<div class="row-fluid page-header">
  <div class="span3">
  </div>
  <div class="span6">
    <div class="well">
      <h3>
        % if success:
          <img src="${request.static_url('ringo:static/images/icons/32x32/dialog-success.png')}"/>
          ${_('User confirmed')}
        % else:
          <img
          src="${request.static_url('ringo:static/images/icons/32x32/dialog-error.png')}"/>
          ${_('User not confirmed')}
        % endif
      </h3>
      ${msg}
    </div>
  </div>
  <div class="span3">
  </div>
</div>

