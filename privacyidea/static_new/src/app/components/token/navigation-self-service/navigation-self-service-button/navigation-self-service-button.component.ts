import { CommonModule } from '@angular/common';
import { Component, computed, inject, Input } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatFabAnchor } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { ContentService } from '../../../../services/content/content.service';
import { TokenService } from '../../../../services/token/token.service';
import { ContainerService } from '../../../../services/container/container.service';
import { TokenSelectedContentKey } from '../../token.component';

@Component({
  selector: 'app-navigation-self-service-button',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatFabAnchor,
    RouterLink,
    RouterLinkActive,
  ],
  templateUrl: './navigation-self-service-button.component.html',
  styleUrl: './navigation-self-service-button.component.scss',
})
export class NavigationSelfServiceButtonComponent {
  private content = inject(ContentService);
  private tokenService = inject(TokenService);
  private containerService = inject(ContainerService);
  private readonly routeMap: Record<
    TokenSelectedContentKey,
    string | (() => string)
  > = {
    token_overview: '/tokens',
    'token_self-service_menu': '/tokens',
    token_enrollment: '/tokens/enroll',
    assign_token: '/tokens/assign-token',
    token_challenges: '/tokens/challenges',
    token_applications: '/tokens/applications',
    token_get_serial: '/tokens/get-serial',
    token_details: () => `/tokens/${this.tokenService.tokenSerial() || ''}`,

    container_overview: '/tokens/containers',
    container_create: '/tokens/containers/create',
    container_details: () =>
      `/tokens/containers/${this.containerService.containerSerial() || ''}`,

    audit: '/audit',
  };
  @Input({ required: true }) key!: TokenSelectedContentKey;
  @Input({ required: true }) title!: string;
  @Input() matIconName?: string;
  @Input() matIconClass?: string;
  @Input() matIconSize?:
    | 'tile-icon-small'
    | 'tile-icon-medium'
    | 'tile-icon-large';
  routePath = computed(() => {
    const e = this.routeMap[this.key];
    return typeof e === 'function' ? e() : e;
  });

  isSelected = computed(() => this.content.selectedContent() === this.key);
}
