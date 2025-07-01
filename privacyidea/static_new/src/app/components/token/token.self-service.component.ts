import { Component } from '@angular/core';
import { TokenComponent } from './token.component';
import { MatCardModule } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatFabButton } from '@angular/material/button';
import { componentFadeAnimation } from '../../../styles/animations/animations';
import { NavigationSelfServiceComponent } from './navigation-self-service/navigation-self-service.component';
import { AssignTokenSelfServiceComponent } from './assign-token-self-service/assign-token-self-service.component';
import { ContainerCreateSelfServiceComponent } from './container-create/container-create.self-service.component';
import { ContainerDetailsSelfServiceComponent } from './container-details/container-details.self-service.component';
import { ContainerTableSelfServiceComponent } from './container-table/container-table.self-service.component';
import { TokenDetailsSelfServiceComponent } from './token-details/token-details.self-service.component';
import { TokenEnrollmentSelfServiceComponent } from './token-enrollment/token-enrollment.self-service.component';
import { AuditComponentSelfServiceComponent } from '../audit/audit.self-service.component';

@Component({
  selector: 'app-token-self-service',
  imports: [
    MatCardModule,
    MatIcon,
    MatFabButton,
    NavigationSelfServiceComponent,
    TokenDetailsSelfServiceComponent,
    TokenEnrollmentSelfServiceComponent,
    AssignTokenSelfServiceComponent,
    ContainerCreateSelfServiceComponent,
    ContainerTableSelfServiceComponent,
    ContainerDetailsSelfServiceComponent,
    AuditComponentSelfServiceComponent,
  ],
  animations: [componentFadeAnimation],
  templateUrl: './token.self-service.component.html',
  styleUrl: './token.component.scss',
})
export class TokenSelfServiceComponent extends TokenComponent {}
