import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserSourcesComponent } from './user-sources.component';
import { ResolverService } from '../../../services/resolver/resolver.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { AuthService } from '../../../services/auth/auth.service';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { MockResolverService } from "../../../../testing/mock-services/mock-resolver-service";
import { MockNotificationService, MockTableUtilsService } from "../../../../testing/mock-services";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";

class LocalMockMatDialog {
  result$ = of(true);
  open = jest.fn(() => ({
    afterClosed: () => this.result$
  }));
}

describe('UserSourcesComponent', () => {
  let component: UserSourcesComponent;
  let fixture: ComponentFixture<UserSourcesComponent>;
  let resolverService: MockResolverService;
  let notificationService: MockNotificationService;
  let dialog: LocalMockMatDialog;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserSourcesComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ResolverService, useClass: MockResolverService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: MatDialog, useClass: LocalMockMatDialog },
        {
          provide: Router,
          useValue: {
            navigate: jest.fn()
          }
        },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => null } }
          }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(UserSourcesComponent);
    component = fixture.componentInstance;
    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialog = TestBed.inject(MatDialog) as unknown as LocalMockMatDialog;
    router = TestBed.inject(Router);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have columns defined', () => {
    expect(component.columnKeys).toContain('resolvername');
    expect(component.columnKeys).toContain('type');
    expect(component.columnKeys).toContain('actions');
  });

  it('should enable create button only when name and type are set', () => {
    component.newResolverName.set('');
    component.newResolverType.set('');
    expect(component.canSubmitNewResolver()).toBeFalsy();

    component.newResolverName.set('test-res');
    component.newResolverType.set('passwdresolver');
    expect(component.canSubmitNewResolver()).toBeTruthy();
  });

  it('should reset create form', () => {
    component.newResolverName.set('test');
    component.newResolverType.set('ldap');
    component.resetCreateForm();
    expect(component.newResolverName()).toBe('');
    expect(component.newResolverType()).toBe('');
  });

  it('onCreateResolver should reset form', () => {
    component.newResolverName.set('new-res');
    component.newResolverType.set('ldapresolver');

    component.onCreateResolver();

    expect(component.newResolverName()).toBe('');
    expect(component.newResolverType()).toBe('');
  });

  it('onEditResolver should set selected resolver and navigate', () => {
    const resolver = { resolvername: 'res1', type: 'sqlresolver' } as any;
    const spy = jest.spyOn(resolverService.selectedResolverName, 'set');
    component.onEditResolver(resolver);

    expect(spy).toHaveBeenCalledWith('res1');
    expect(router.navigate).toHaveBeenCalledWith(['users/new-resolver']);
  });

  it('onDeleteResolver should delete after confirmation', () => {
    dialog.result$ = of(true);
    const resolver = { resolvername: 'res1' } as any;

    component.onDeleteResolver(resolver);

    expect(dialog.open).toHaveBeenCalled();
    expect(resolverService.deleteResolver).toHaveBeenCalledWith('res1');
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining('deleted'));
  });

  it('onDeleteResolver should not delete if cancelled', () => {
    dialog.result$ = of(false);
    const resolver = { resolvername: 'res1' } as any;

    component.onDeleteResolver(resolver);

    expect(dialog.open).toHaveBeenCalled();
    expect(resolverService.deleteResolver).not.toHaveBeenCalled();
  });
});