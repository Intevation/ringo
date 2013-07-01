<div class="container">
  <div class="navbar">
    % if len(h.get_modules(request, 'admin-menu')) > 0:
    <ul class="nav">
      <li class="dropdown dropup">
        <a href="#" data-toggle="dropdown"><img src="${request.static_url('ringo:static/images/icons/16x16/applications-system.png')}"/>${_('Administration')}<b class="caret"></b></a>
        <ul class="dropdown-menu dropup-menu" role="menu">
          % for modul in h.get_modules(request, 'admin-menu'):
            <li><a href="${request.route_url(modul.name+'-list')}">${modul.get_label(plural=True)}</a></li>
          % endfor
        </ul>
      </li>
    </ul>
    % endif
    <ul class="nav pull-right">
      <li>
        <a href="${request.route_url('about')}">${_('About')}</a>
      </li>
      <li>
        <a href="${request.route_url('contact')}">${_('Contact')}</a>
      </li>
      <li>
        <a href="${request.route_url('version')}" title="${_('Show version information')}">${h.get_app_title()} ver. ${h.get_app_version()}</a>
      </li>
    </ul>
  </div>
</div>
