import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { share } from 'rxjs/operators';
import { LoadingService } from '../../services/loading/loading-service';

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loadingService = inject(LoadingService);

  const sharedRequest$ = next(req).pipe(share());

  loadingService.addLoading({ key: req.url, observable: sharedRequest$ });

  return sharedRequest$;
};
