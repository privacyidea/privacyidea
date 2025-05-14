import { Component, inject } from '@angular/core';
import { TokenComponent } from './token.component';
import { MatCardModule } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatFabAnchor, MatFabButton } from '@angular/material/button';
import { VersionService } from '../../services/version/version.service';
import { TokenEnrollmentSelfServiceComponent } from './token-enrollment/token-enrollment.self-service.component';
import { AssignTokenSelfServiceComponent } from './assign-token-self-service/assign-token-self-service.component';
import { ContainerCreateSelfServiceComponent } from './container-create/container-create.self-service.component';
import { TokenTableSelfServiceComponent } from './token-table/token-table.self-service.component';
import { ContainerTableSelfServiceComponent } from './container-table/container-table.self-service.component';
import { TokenDetailsSelfServiceComponent } from './token-details/token-details.self-service.component';
import { ContainerDetailsSelfServiceComponent } from './container-details/container-details.self-service.component';
import { componentFadeAnimation } from '../../../styles/animations/animations';

@Component({
  selector: 'app-token-self-service',
  imports: [
    MatCardModule,
    MatIcon,
    MatFabAnchor,
    TokenDetailsSelfServiceComponent,
    TokenEnrollmentSelfServiceComponent,
    MatFabButton,
    AssignTokenSelfServiceComponent,
    ContainerCreateSelfServiceComponent,
    TokenTableSelfServiceComponent,
    ContainerTableSelfServiceComponent,
    ContainerDetailsSelfServiceComponent,
  ],
  animations: [componentFadeAnimation],
  templateUrl: './token.self-service.component.html',
  styleUrl: './token.component.scss',
})
export class TokenSelfServiceComponent extends TokenComponent {
  selectedContent = this.contentService.selectedContent;
  versionService = inject(VersionService);
}
