import { Component, inject } from '@angular/core';
import { TokenComponent } from './token.component';
import { MatCardModule } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatFabAnchor, MatFabButton } from '@angular/material/button';
import { ContainerDetailsComponent } from './container-details/container-details.component';
import { TokenDetailsComponent } from './token-details/token-details.component';
import { VersionService } from '../../services/version/version.service';
import { TokenEnrollmentSelfServiceComponent } from './token-enrollment/token-enrollment.self-service.component';
import { AssignTokenSelfServiceComponent } from './assign-token-self-service/assign-token-self-service.component';
import { ContainerCreateSelfServiceComponent } from './container-create/container-create.self-service.component';
import { TokenTableSelfServiceComponent } from './token-table/token-table.self-service.component';
import { ContainerTableSelfServiceComponent } from './container-table/container-table.self-service.component';

@Component({
  selector: 'app-token-self-service',
  imports: [
    MatCardModule,
    MatIcon,
    MatFabAnchor,
    ContainerDetailsComponent,
    TokenDetailsComponent,
    TokenEnrollmentSelfServiceComponent,
    MatFabButton,
    AssignTokenSelfServiceComponent,
    ContainerCreateSelfServiceComponent,
    TokenTableSelfServiceComponent,
    ContainerTableSelfServiceComponent,
  ],
  templateUrl: './token.self-service.component.html',
  styleUrl: './token.component.scss',
})
export class TokenSelfServiceComponent extends TokenComponent {
  selectedContent = this.contentService.selectedContent;
  versionService = inject(VersionService);
}
