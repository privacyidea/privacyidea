import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ContainerDetailsTokenTableComponent } from './container-details-token-table.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AuthService } from '../../../../services/auth/auth.service';
import { ContainerService } from '../../../../services/container/container.service';
import { TokenService } from '../../../../services/token/token.service';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Router } from '@angular/router';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { MatTableDataSource } from '@angular/material/table';

describe('ContainerDetailsTokenTableComponent', () => {
  let component: ContainerDetailsTokenTableComponent;
  let fixture: ComponentFixture<ContainerDetailsTokenTableComponent>;
  let authServiceSpy: jasmine.SpyObj<AuthService>;
  let containerServiceSpy: jasmine.SpyObj<ContainerService>;
  let tokenServiceSpy: jasmine.SpyObj<TokenService>;
  let tableUtilsSpy: jasmine.SpyObj<TableUtilsService>;
  let overflowServiceSpy: jasmine.SpyObj<OverflowService>;
  let notificationServiceSpy: jasmine.SpyObj<NotificationService>;
  let routerSpy: jasmine.SpyObj<Router>;
  let matDialogSpy: jasmine.SpyObj<MatDialog>;

  beforeEach(async () => {
    authServiceSpy = jasmine.createSpyObj('AuthService', [
      'isAuthenticatedUser',
    ]);
    containerServiceSpy = jasmine.createSpyObj('ContainerService', [
      'removeTokenFromContainer',
      'toggleAll',
      'deleteAllTokens',
    ]);
    tokenServiceSpy = jasmine.createSpyObj('TokenService', ['toggleActive']);
    tableUtilsSpy = jasmine.createSpyObj('TableUtilsService', [
      'handleColumnClick',
      'getClassForColumnKey',
      'isLink',
      'getClassForColumn',
      'getDisplayText',
    ]);
    overflowServiceSpy = jasmine.createSpyObj('OverflowService', [
      'handleFilterInput',
      'isWidthOverflowing',
    ]);
    notificationServiceSpy = jasmine.createSpyObj('NotificationService', [
      'openSnackBar',
    ]);
    routerSpy = jasmine.createSpyObj('Router', ['navigate']);
    matDialogSpy = jasmine.createSpyObj('MatDialog', ['open']);

    authServiceSpy.isAuthenticatedUser.and.returnValue(true);
    routerSpy.navigate.and.returnValue(Promise.resolve(true));

    containerServiceSpy.removeTokenFromContainer.and.returnValue(of({}));
    containerServiceSpy.toggleAll.and.returnValue(of({}));
    containerServiceSpy.deleteAllTokens.and.returnValue(of({}));
    tokenServiceSpy.toggleActive.and.returnValue(of({}));

    matDialogSpy.open.and.returnValue({
      afterClosed: () => of(true),
    } as MatDialogRef<ConfirmationDialogComponent>);

    await TestBed.configureTestingModule({
      imports: [ContainerDetailsTokenTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceSpy },
        { provide: ContainerService, useValue: containerServiceSpy },
        { provide: TokenService, useValue: tokenServiceSpy },
        { provide: TableUtilsService, useValue: tableUtilsSpy },
        { provide: OverflowService, useValue: overflowServiceSpy },
        { provide: NotificationService, useValue: notificationServiceSpy },
        { provide: Router, useValue: routerSpy },
        { provide: MatDialog, useValue: matDialogSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsTokenTableComponent);
    component = fixture.componentInstance;

    component.dataSource = signal(
      new MatTableDataSource<any>([
        {
          serial: 'Mock serial',
          tokentype: 'hotp',
          active: true,
          username: 'userA',
        },
        {
          serial: 'Another serial',
          tokentype: 'totp',
          active: false,
          username: 'userB',
        },
      ]),
    );
    component.containerSerial = signal('CONT-1');
    component.tokenSerial = signal('');
    component.refreshContainerDetails = signal(false);
    component.isProgrammaticChange = signal(false);
    component.selectedContent = signal('container_details');

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngAfterViewInit', () => {
    it('should set paginator and sort on dataSource', () => {
      const ds = component.dataSource();
      expect(ds.paginator).toBe(component.paginator);
      expect(ds.sort).toBe(component.sort);
    });
  });

  describe('handleFilterInput', () => {
    it('should set the dataSource filter value', () => {
      const mockEvent = {
        target: { value: ' testFilter ' },
      } as unknown as Event;

      component.handleFilterInput(mockEvent);

      expect(component.filterValue).toBe('testFilter');
      expect(component.dataSource().filter).toBe('testfilter');
    });
  });

  describe('tokenSelected', () => {
    it('should set signals for isProgrammaticChange and tokenSerial, and selectedContent', () => {
      expect(component.isProgrammaticChange()).toBeFalse();
      component.tokenSelected('Mock serial');

      expect(component.isProgrammaticChange()).toBeTrue();
      expect(component.tokenSerial()).toBe('Mock serial');
      expect(component.selectedContent()).toBe('token_details');
    });
  });

  describe('removeTokenFromContainer', () => {
    it('should call containerService.removeTokenFromContainer and set refreshContainerDetails true', () => {
      component.refreshContainerDetails.set(false);

      component.removeTokenFromContainer('CONT-1', 'Mock serial');
      expect(containerServiceSpy.removeTokenFromContainer).toHaveBeenCalledWith(
        'CONT-1',
        'Mock serial',
      );

      expect(component.refreshContainerDetails()).toBeTrue();
    });

    it('should call notificationService on error', () => {
      containerServiceSpy.removeTokenFromContainer.and.returnValue(
        throwError(() => new Error('Remove failed')),
      );

      component.removeTokenFromContainer('CONT-1', 'Mock serial');
      expect(notificationServiceSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to remove token from container. ',
      );
    });
  });

  describe('handleColumnClick', () => {
    it('should call toggleActive if columnKey === active', () => {
      spyOn(component, 'toggleActive');
      const element = { serial: 'Mock serial', active: true };

      component.handleColumnClick('active', element);
      expect(component.toggleActive).toHaveBeenCalledWith(element);
    });

    it('should do nothing if columnKey != active', () => {
      spyOn(component, 'toggleActive');
      component.handleColumnClick('username', {});

      expect(component.toggleActive).not.toHaveBeenCalled();
    });
  });

  describe('toggleActive', () => {
    it('should call tokenService.toggleActive and set refreshContainerDetails on success', () => {
      component.refreshContainerDetails.set(false);
      const element = { serial: 'Mock serial', active: true };

      component.toggleActive(element);

      expect(tokenServiceSpy.toggleActive).toHaveBeenCalledWith(
        'Mock serial',
        true,
      );
      expect(component.refreshContainerDetails()).toBeTrue();
    });

    it('should call notificationService on error', () => {
      tokenServiceSpy.toggleActive.and.returnValue(
        throwError(() => new Error('Toggle error')),
      );

      component.toggleActive({ serial: 'Mock serial', active: true });
      expect(notificationServiceSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to toggle active. ',
      );
    });
  });

  describe('toggleAll', () => {
    it('should call containerService.toggleAll and set refreshContainerDetails on success', () => {
      component.refreshContainerDetails.set(false);

      component.toggleAll('activate');
      expect(containerServiceSpy.toggleAll).toHaveBeenCalledWith(
        'CONT-1',
        'activate',
      );
      expect(component.refreshContainerDetails()).toBeTrue();
    });

    it('should call notificationService on error', () => {
      containerServiceSpy.toggleAll.and.returnValue(
        throwError(() => new Error('ToggleAll error')),
      );

      component.toggleAll('activate');
      expect(notificationServiceSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to toggle all. ',
      );
    });
  });

  describe('deleteAllTokens', () => {
    it('should open a confirmation dialog and call deleteAllTokens on confirm', () => {
      component.deleteAllTokens();

      expect(matDialogSpy.open).toHaveBeenCalledWith(
        ConfirmationDialogComponent,
        {
          data: {
            serial_list: ['Mock serial', 'Another serial'],
            title: 'Delete All Tokens',
            type: 'token',
            action: 'delete',
            numberOfTokens: 2,
          },
        },
      );

      expect(containerServiceSpy.deleteAllTokens).toHaveBeenCalledWith(
        'CONT-1',
        'Mock serial,Another serial',
      );
      expect(component.refreshContainerDetails()).toBeTrue();
    });

    it('should not call deleteAllTokens if dialog result is false (cancel)', () => {
      matDialogSpy.open.and.returnValue({
        afterClosed: () => of(false),
      } as MatDialogRef<ConfirmationDialogComponent>);

      containerServiceSpy.deleteAllTokens.calls.reset();
      component.deleteAllTokens();

      expect(containerServiceSpy.deleteAllTokens).not.toHaveBeenCalled();
    });

    it('should call notificationService on error', () => {
      containerServiceSpy.deleteAllTokens.and.returnValue(
        throwError(() => new Error('DeleteAll error')),
      );

      component.deleteAllTokens();
      expect(notificationServiceSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to delete all tokens. ',
      );
    });
  });
});
