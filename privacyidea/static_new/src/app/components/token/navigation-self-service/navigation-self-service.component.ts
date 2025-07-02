import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { ContentService } from '../../../services/content/content.service';
import {
  NavigationSelfServiceButtonComponent,
  NavigationSelfServiceButtonData,
} from './navigation-self-service-button/navigation-self-service-button.component';

@Component({
  selector: 'app-navigation-self-service',
  standalone: true,
  imports: [CommonModule, MatIconModule, NavigationSelfServiceButtonComponent],
  templateUrl: './navigation-self-service.component.html',
  styleUrl: './navigation-self-service.component.scss',
})
export class NavigationSelfServiceComponent {
  navigationSelfServiceButtons: NavigationSelfServiceButtonData[] = [
    {
      key: 'token_enrollment',
      title: 'Token Enrollment',
      matIconName: 'add_moderator',
    },
    {
      key: 'assign_token',
      title: 'Assign Token',
      matIconName: 'admin_panel_settings',
      matIconSize: 'tile-icon-large',
    },
    {
      key: 'container_overview',
      title: 'Container Overview',
      matIconClass: 'mdi--folder-search',
    },
    {
      key: 'container_create',
      title: 'Create Container',
      matIconName: 'create_new_folder',
    },
    { key: 'audit', title: 'Audit Log', matIconName: 'manage_search' },
  ];

  selectedContent = this.contentService.selectedContent;
  constructor(protected readonly contentService: ContentService) {}
}
