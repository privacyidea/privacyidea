import { Component, inject } from '@angular/core';
import { TokenComponent } from './token.component';
import { MatCardModule } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatFabAnchor, MatFabButton } from '@angular/material/button';
import { ContainerDetailsComponent } from './container-details/container-details.component';
import { ContainerTableComponent } from './container-table/container-table.component';
import { TokenDetailsComponent } from './token-details/token-details.component';
import { TokenTableComponent } from './token-table/token-table.component';
import { VersionService } from '../../services/version/version.service';
import { TokenEnrollmentSelfServiceComponent } from './token-enrollment/token-enrollment.self-service.component';
import { AssignTokenSelfServiceComponent } from './assign-token-self-service/assign-token-self-service.component';
import { ContainerCreateSelfServiceComponent } from './container-create/container-create.self-service.component';

@Component({
  selector: 'app-token-self-service',
  imports: [
    MatCardModule,
    MatIcon,
    MatFabAnchor,
    ContainerDetailsComponent,
    ContainerTableComponent,
    TokenDetailsComponent,
    TokenEnrollmentSelfServiceComponent,
    TokenTableComponent,
    MatFabButton,
    AssignTokenSelfServiceComponent,
    ContainerCreateSelfServiceComponent,
  ],
  templateUrl: './token.self-service.component.html',
  styleUrl: './token.component.scss',
})
export class TokenSelfServiceComponent extends TokenComponent {
  selectedContent = this.contentService.selectedContent;
  versionService = inject(VersionService);
}
